const API = "http://localhost:5000"; 
// backend API URL

let barChart;
let scatterChart;
let pieChart;

// buttons from the UI
document.getElementById("getClusters").addEventListener("click", loadClusters);
document.getElementById("getInsights").addEventListener("click", loadInsights);
document.getElementById("getRecipes").addEventListener("click", loadPieChart);


// loads the bar chart from the clusters API
function loadClusters(){

fetch(API + "/clusters")
.then(res => res.json())
.then(data => {

console.log("Clusters:", data); // check API data in console

const diets = Object.keys(data);

const protein = diets.map(d => data[d]["Protein(g)"]);
const carbs = diets.map(d => data[d]["Carbs(g)"]);
const fat = diets.map(d => data[d]["Fat(g)"]);

const ctx = document.getElementById("barChart").getContext("2d");

// remove old chart if user clicks again
if(barChart){
barChart.destroy();
}



// create bar chart
barChart = new Chart(ctx,{
type:"bar",
data:{
labels:diets,
datasets:[
{ label:"Protein", data:protein },
{ label:"Carbs", data:carbs },
{ label:"Fat", data:fat }
]
},
options:{ responsive:true }
});

});
}


// loads scatter plot from insights API
function loadInsights(){

fetch(API + "/insights")
.then(res => res.json())
.then(data => {

const points = Object.values(data).map(item => ({
x:item["Protein_to_Carbs_ratio"],
y:item["Carbs_to_Fat_ratio"]
}));

const ctx = document.getElementById("scatterChart").getContext("2d");

if(scatterChart){
scatterChart.destroy();
}

// create scatter chart
scatterChart = new Chart(ctx,{
type:"scatter",
data:{
datasets:[
{ label:"Nutrition Ratios", data:points }
]
}
});

});
}


// loads pie chart using clusters data
function loadPieChart(){

fetch(API + "/clusters")
.then(res => res.json())
.then(data => {

const diets = Object.keys(data);
const protein = diets.map(d => data[d]["Protein(g)"]);

const ctx = document.getElementById("pieChart").getContext("2d");

if(pieChart){
pieChart.destroy();
}

// create pie chart
pieChart = new Chart(ctx,{
type:"pie",
data:{
labels:diets,
datasets:[
{ data:protein }
]
}
});

});
}