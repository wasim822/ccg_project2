import os
from io import BytesIO
import warnings

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from azure.storage.blob import BlobServiceClient
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

warnings.filterwarnings("ignore")


def fixDataset(odf: pd.DataFrame) -> pd.DataFrame:
    df = odf.copy()
    df.fillna(df.mean(numeric_only=True), inplace=True)
    df["Protein_to_Carbs_ratio"] = df["Protein(g)"] / df["Carbs(g)"].replace(0, 1)
    df["Carbs_to_Fat_ratio"] = df["Carbs(g)"] / df["Fat(g)"].replace(0, 1)
    return df


DIET_TYPES = ["dash", "keto", "mediterranean", "paleo", "vegan"]


def whitelistInput(value: str | None) -> str | None:
    if value is not None:
        result = value.lower()
        if result not in DIET_TYPES:
            return None
        return result
    return None


def loadDataset() -> pd.DataFrame:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER", "data")
    blob_name = os.getenv("BLOB_FILE", "All_Diets.csv")

    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name
    )

    stream = blob_client.download_blob()
    csv_bytes = stream.readall()

    df = pd.read_csv(BytesIO(csv_bytes))
    return df


@app.get("/")
def home():
    return send_from_directory(".", "index.html")


@app.get("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.get("/style.css")
def style():
    return send_from_directory(".", "style.css")


@app.get("/recipes")
@app.get("/recipies")
def recipes():
    try:
        dietType = request.values.get("dietType")
        dietType = whitelistInput(dietType)

        df = loadDataset()
        df = fixDataset(df)

        results = df
        if dietType is not None:
            results = results.loc[results["Diet_type"] == dietType]

        results = results[["Recipe_name", "Cuisine_type", "Protein(g)", "Carbs(g)", "Fat(g)"]]
        results = results.to_dict(orient="index")

        return jsonify(results), 200

    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "Azure Blob Storage"
        }), 404

    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv from Azure Blob",
            "details": str(e)
        }), 500


@app.get("/insights")
def insights():
    try:
        dietType = request.values.get("dietType")
        dietType = whitelistInput(dietType)

        df = loadDataset()
        df = fixDataset(df)

        value = df
        if dietType is not None:
            value = value.loc[value["Diet_type"] == dietType]

        value = value[["Recipe_name", "Protein_to_Carbs_ratio", "Carbs_to_Fat_ratio"]]
        value = value.to_dict(orient="index")

        return jsonify(value), 200

    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "Azure Blob Storage"
        }), 404

    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv from Azure Blob",
            "details": str(e)
        }), 500


@app.get("/clusters")
def clusters():
    try:
        df = loadDataset()
        df = fixDataset(df)

        value = df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]].mean()
        value = value.to_dict(orient="index")

        return jsonify(value), 200

    except FileNotFoundError:
        return jsonify({
            "error": "All_Diets.csv not found",
            "expected_path": "Azure Blob Storage"
        }), 404

    except Exception as e:
        return jsonify({
            "error": "failed to read All_Diets.csv from Azure Blob",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)