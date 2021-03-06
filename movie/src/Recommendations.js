import React from "react";
import axios from "axios";
import { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { selectUser } from "./state/userSlice";
import Button from "@mui/material/Button";
import { SingleMovie } from "./SingleMovie";
import Backdrop from "@mui/material/Backdrop";
import CircularProgress from "@mui/material/CircularProgress";

export const Recommendations = () => {
  const user = useSelector(selectUser);
  const token = sessionStorage.getItem("token");
  const [recommendations, setRecommendations] = useState();
  const [movies, setMovies] = useState();
  const [recommendationId, setRecommendationId] = useState([]);
  const [loaded, setLoaded] = useState(true);
  const [extractedMovies, setExtractedMovies] = useState([]);

  const refreshRecommendations = async () => {
    setLoaded(false);
    console.log(user.email);
    console.log("token ", token);
    const options = {
      method: "POST",
      // tell backend that this data will be json because that's what its expecting
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      //convert email and password to a json string
    };

    const response = await fetch(`/recommend`, options);
    const json = await response.json();
    console.log(json);
    if (response.status === 200) {
      console.log(Object.values(json));
      setRecommendations(json);
      setLoaded(true);
      return json;
    }
  };

  //get list of recommendations from backend
  const fetchRecs = async () => {
    const options = {
      method: "POST",
      // tell backend that this data will be json because that's what its expecting
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      //convert email and password to a json string
    };

    const response = await fetch(`/recommendations`, options);
    const json = await response.json();
    //console.log(json);
    if (response.status === 200) {
      setRecommendations(json);
      return json;
    }
  };

  //get movie details from TMDB
  const fetchMovies = async () => {
    //iterate through likes object to make concurrent requests
    const { data } = axios
      .all(
        recommendations.map((u) =>
          axios.get(
            `https://api.themoviedb.org/3/search/movie?api_key=${process.env.REACT_APP_API}&query=${u.recommendation}`
          )
        )
      )
      //take the result of all of those requests and set it to movies
      .then(
        axios.spread((...res) => {
          //console.log(res);
          setMovies(res);
        })
      );
  };

  const parseMovies = (data) => {
    var match;
    var i;
    var z;
    for(i=0; i<recommendations.length; i++){
      for(z=0; z<data.length;z++){
        //console.log(recommendations[i].recommendation.valueOf(), "===", data[z].title.valueOf())
        if(recommendations[i].recommendation.valueOf() === data[z].title.valueOf() ){
          console.log("MATCH!")
          if(data[z].backdrop_path!=null){
            match=data[z];
          }
          else{
            continue;
          }
          
          //console.log(matches);
          return match;
        }
      }
    }

  };

  useEffect(() => {
    if (user != null) {
      fetchRecs();
    }
  }, []);

  useEffect(() => {
    if (recommendations != null) {
      console.log(recommendations);
      fetchMovies();
    }
  }, [recommendations]);

  // useEffect(() => {
  //   //extract recommendation ids
  //   var matches= new Array();
  //   if (movies != null) {
  //     //var result= movies.map(a=>a.data.results[0].id)
  //     //console.log(result)
  //     //console.log(user)
  //     movies.map((u) => matches.push(parseMovies(u.data.results)));
  //   }
  //   console.log(matches)
  // }, [movies]);

  useEffect(() => {
    fetchRecs();
    if (movies != null) {
      fetchMovies();
    }
  }, [user]);

  useEffect(()=>{
    console.log(extractedMovies);
  },[extractedMovies])
  return (
    <div>
      <span className="LikedMovies__Title"> Recommended Movies </span>
      <div>
        <Button
          variant="contained"
          size="small"
          onClick={refreshRecommendations}
        >
          Refresh
        </Button>
        {loaded == false && loaded != true && (
          <Backdrop
            sx={{ color: "#fff", zIndex: (theme) => theme.zIndex.drawer + 1 }}
            open
          >
            <CircularProgress color="inherit" />
          </Backdrop>
        )}
      </div>
      <div className="MovieList">
        {/* if content is not empty and  */}
        {movies &&
          movies.map((c) => (
            <SingleMovie
              key={c.data.results[0].id}
              id={c.data.results[0].id}
              poster={c.data.results[0].poster_path}
              title={c.data.results[0].title}
              date={c.data.results[0].release_date}
              vote_average={c.data.results[0].vote_average}
            />
          ))}
      </div>
    </div>
  );
};
