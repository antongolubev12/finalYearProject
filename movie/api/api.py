from re import U
import re
import jwt
from sqlalchemy.sql.expression import false
from sqlalchemy.sql.functions import user
from db import app, User, db, Likes, Recommendations,Dislikes
from sqlalchemy import func,delete
from flask import jsonify,request,json
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
import os
from queries import check_user,get_user_details,get_password,check_likes,get_all_likes,delete_like,check_df,get_rec_id,check_rec,get_all_recommendations,delete_recommendations_by_og_movie,compare_likes_to_recs,check_dislikes,get_all_dislikes,delete_recommendations,delete_dislike
from serializers import user_serializer, movie_serializer,like_serializer,recommender_serializer,recommendation_serializer
from prepare_like import push_like_to_data
from recommender import recommend_movies

#generate salt for bcrypt
salt=bcrypt.gensalt()

# Create a route to authenticate your users and return JWTs. The
# create_access_token() function is used to actually generate the JWT.
@app.route('/token', methods=['POST'])
def create_auth_token():
    #get email from the request data
    email = request.json.get("email")

    #get password from the request data
    password = request.json.get("password",None)
    
    #query db to see if a user id that has the passed email exists
    exists=check_user(email)
    print("User exists: ", exists)
    
    if exists==False:
        print("User does not exist")
        return jsonify({"msg": "An account with this email does not exist!"}), 401

    user= get_user_details(email)
    
    #retrieve hash password from db
    hash=get_password(email)

    print("Hash: ", hash)

    #if given password does not match hash password on db then return error
    #password from front end has to be encoded because cryptographic functions only work on byte strings
    #running a SELECT returns a tuple, so hash[0] is needed because I only want the first element of the tuple
    if not bcrypt.checkpw(password.encode('utf-8'),hash[0]):
        print("Password is wrong")
        return jsonify({"msg": "Incorrect password!"}), 401
    

    #create access token
    access_token = create_access_token(identity=email,expires_delta=False)
    
    print("token: "+access_token)

    #serialize data into json format and append the access token onto it
    data=user_serializer(user,access_token)
    
    return jsonify(data)

@app.route('/register',methods=['POST'])
def register():
    print("In api.register()")

    #convert request data to python dictionary 
    request_data = json.loads(request.data)
    print("loaded json")
    
    print("Passed pw: ",request_data['password'])

    #Check if user exists
    exists = check_user(request_data['email'])

    #validation
    if exists:
        print("email already exists ")
        return jsonify({"msg": "User with this email already exists!"}), 401

    elif not request_data['fname'] or not request_data['lname'] :
        return jsonify({"msg": "Name is not valid!"}), 401

    elif not request_data['email'] or '@' not in request_data['email'] or '.com' not in request_data['email'] :
        return jsonify({"msg": "Email is not valid!"}), 401

    elif not request_data['password'] :
        return jsonify({"msg": "Password is not valid!"}), 401

    #find the latest user's id
    biggest_id=db.session.query(func.max(User.user_id)).scalar()
    if biggest_id == None:
        biggest_id=-1

    #set the next id to be id+1
    id= biggest_id+1

    # Hash a password for the first time, with a randomly-generated salt
    hashed = bcrypt.hashpw(request_data['password'].encode('utf-8'), salt)
    print("Password hashed: ",hashed)

    print(request_data)
    
    #map the response from front end to user model
    user= User(user_id=id,
    fname=request_data['fname'],
    lname=request_data['lname'],
    email=request_data['email'],
    password=hashed)

    #push to database
    db.session.add(user)
    db.session.commit()

    return{'201': 'user created successfully'}

@app.route('/like',methods=['POST'])
#decorator states that you need a jwt token to access this api endpoint
@jwt_required()
def add_like():
    print("In api.like()")
    #convert to python dictionary 
    request_data = json.loads(request.data)
    #print(request.headers)
    #print(request_data)

    if request_data['movie_id'] is None:
        return jsonify({"msg": "INVALID MOVIE"}), 401
    
    #Gets email of user from the jwt token from the payload of the token.
    #The email was specified as the identity when it was created
    email=get_jwt_identity()
    print("email :",email)

    #fetch user details using the email
    user=get_user_details(email)
    print("User id",user.user_id)

    #if like already exists then unlike
    if check_likes(request_data['movie_id'],user.user_id) :
        delete_like(request_data['movie_id'],user.user_id)
        delete_recommendations_by_og_movie(user.user_id,request_data['title'])
        return jsonify({"msg": "Movie unliked"}), 200

    request_data['keywords']=json.dumps(request_data['keywords'])
    request_data['cast']=json.dumps(request_data['cast'])
    request_data['crew']=json.dumps(request_data['crew'])
    request_data['genres']=json.dumps(request_data['genres'])

    like=Likes(movie_id=request_data['movie_id'],
        title=request_data['title'],
        genres=request_data['genres'],
        overview=request_data['overview'],
        keywords=request_data['keywords'],
        cast=request_data['cast'],
        crew=request_data['crew'],
        user_id=user.user_id
    )

    #add the users like to the dataframe on the database
    add_to_df(request_data)

    db.session.add(like)
    db.session.commit()
    
    return{'201': 'added like successfully'}

@app.route('/dislike',methods=['POST'])
#decorator states that you need a jwt token to access this api endpoint
@jwt_required()
def dislike():
    print("In api.dislike()")

    #convert to python dictionary 
    request_data = json.loads(request.data)

    if request_data['movie_id'] is None:
        return jsonify({"msg": "INVALID MOVIE"}), 401
    
    #Gets email of user from the jwt token from the payload of the token.
    #The email was specified as the identity when it was created
    email=get_jwt_identity()

    #fetch user details using the email
    user=get_user_details(email)

    #if like already exists then unlike
    if check_likes(request_data['movie_id'],user.user_id) :
        delete_like(request_data['movie_id'],user.user_id)

    if check_dislikes(request_data['title'],user.user_id):
        delete_dislike(request_data['movie_id'],user.user_id)
        print("removed disliked")
        return {'201': 'removed dislike successfully'}

    if check_rec(request_data['title'],user.user_id):
        delete_recommendations(user.user_id,request_data['title'])
        
    dislike=Dislikes(movie_id=request_data['movie_id'],
        title=request_data['title'],
        user_id=user.user_id
    )

    db.session.add(dislike)
    db.session.commit()

    print("added dislike")
    
    return{'201': 'added dislike successfully'}


def add_to_df(like):
    if not check_df(like['movie_id']):
        push_like_to_data(like)
    return

@app.route('/getLikes',methods=['POST'])
@jwt_required()
def get_likes():
    email=get_jwt_identity()
    user=get_user_details(email)
    likes=get_all_likes(user.user_id)
    
    likes_list=[]

    for x in likes:
        likes_list.append(like_serializer(x))
        
    print(likes_list)
    return jsonify(likes_list)

@app.route('/getDislikes',methods=['POST'])
@jwt_required()
def get_dislikes():
    email=get_jwt_identity()
    user=get_user_details(email)
    likes=get_all_dislikes(user.user_id)
    
    dislikes_list=[]

    for x in likes:
        dislikes_list.append(like_serializer(x))
        
    print(dislikes_list)
    return jsonify(dislikes_list)

@app.route('/recommend',methods=['POST'])
@jwt_required()
def recommend():
    email=get_jwt_identity()
    user=get_user_details(email)
    likes=get_all_likes(user.user_id)

    likes_list=[]

    for x in likes:
        if not compare_likes_to_recs(x,user.user_id):
            likes_list.append(recommender_serializer(x))
        else:
            continue
    
    print("list of likes to send to algorithm:",likes_list)
    if len(likes_list)>0:
        recommendations=recommend_movies(likes_list)
    else:
        return show_recommendations()
    print("recs:", recommendations)

    #find the latest user's id
    #cast to int
    biggest_id=get_rec_id()

    if biggest_id == None:
        biggest_id=-1

    biggest_id=int(biggest_id)
    print("biggest id:",biggest_id)
    
    #set the next id to be id+1
    id= biggest_id+1

    #extract key and value from dictionary
    for original,recommended in recommendations.items():
        print("og: ",original)
        print("recommendation: ", recommended)

        #remove duplicates if there are any
        #turns list into dictionary which cannot have duplicates, then turns it back into a list
        recommended=list(dict.fromkeys(recommended))
        #loop over recommendations list
        for i in recommended:
            #if i isn't already in the recommendation table
            if not check_rec(i,user.user_id):
                #if i isn't a disliked movie
                if not check_dislikes(i,user.user_id):
                    movie_rec=Recommendations(movie_id=id,title=i,og_movie=original,user_id=user.user_id)
                    id+=1
                    db.session.add(movie_rec)
                    db.session.commit()
                    print("pushed recommendation to db")

    return show_recommendations()

@app.route('/recommendations',methods=['POST'])
@jwt_required()
def show_recommendations():
    print("In /recommendations")
    email=get_jwt_identity()
    user=get_user_details(email)
    recommendations=get_all_recommendations(user.user_id)

    recommendations_list=[]

    for x in recommendations:
        recommendations_list.append(recommendation_serializer(x))

    print(recommendations_list)
    return jsonify(recommendations_list)
    

if __name__=='__main__':
    app.run(debug=True)
    