import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import warnings
from flask import Flask, jsonify, request

app = Flask(__name__)

# suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def fixDataset(odf):
    # Creates a copy from the original df
    df = odf

    # handle missing data (fill missing values with mean for numeric columns only)
    df.fillna(df.mean(numeric_only=True), inplace=True)
    print("Missing values handled")

    # add new metrics (protein-to-carbs ratio and carbs-to-fat ratio)
    df['Protein_to_Carbs_ratio'] = df['Protein(g)'] / df['Carbs(g)']
    df['Carbs_to_Fat_ratio'] = df['Carbs(g)'] / df['Fat(g)']

    return df

# List of possible diet types
DIET_TYPES = ["dash", "keto", "mediterranean", "paleo", "vegan"]

def whitelistInput(value: str):
    # Checks if the value exists
    if value != None:
        result = value.lower()
        # Goes through DIET_TYPES to see if there's a match
        if result not in DIET_TYPES:
            return None
        return result
    return None


@app.get("/recipies")

def recipies():
    try:
        dietType = request.values.get("dietType")
        dietType = whitelistInput(dietType)
        
        # load the dataset
        df = pd.read_csv('All_Diets.csv')
        print(f"Dataset loaded. Total recipes: {len(df)}")
        
        df = fixDataset(df)

        # Get these values back
        value = df
        if dietType != None:
            value = value.loc[value['Diet_type'] == dietType]
        value = value[["Recipe_name", "Cuisine_type", "Protein(g)", "Carbs(g)", "Fat(g)"]]
        value = value.to_dict("index")

        return jsonify(value), 200
    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "All_Diets.csv"
        }), 404
    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv",
            "details": str(e)
        }), 500
    
@app.get("/insights")

def insights():
    try:
        dietType = request.values.get("dietType")
        dietType = whitelistInput(dietType)
        
        # load the dataset
        df = pd.read_csv('All_Diets.csv')
        print(f"Dataset loaded. Total recipes: {len(df)}")
        
        df = fixDataset(df)

        # Get these values back
        value = df
        if dietType != None:
            value = value.loc[value['Diet_type'] == dietType]
        value = value[["Recipe_name", "Protein_to_Carbs_ratio", "Carbs_to_Fat_ratio"]]
        value = value.to_dict("index")

        return jsonify(value), 200
    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "All_Diets.csv"
        }), 404
    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv",
            "details": str(e)
        }), 500
    
@app.get("/clusters")

def clusters():
    try:        
        # load the dataset
        df = pd.read_csv('All_Diets.csv')
        print(f"Dataset loaded. Total recipes: {len(df)}")
        
        df = fixDataset(df)

        # Get the average macros of each diet type
        value = df.groupby('Diet_type')[['Protein(g)', 'Carbs(g)', 'Fat(g)']].mean()
        value = value.to_dict("index")

        return jsonify(value), 200
    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "All_Diets.csv"
        }), 404
    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    # Listen on all interfaces for Docker
    app.run(host="0.0.0.0", port=5000)