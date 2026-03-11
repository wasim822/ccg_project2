import argparse
import os
from io import BytesIO
import warnings

import pandas as pd
from azure.storage.blob import BlobServiceClient
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

warnings.filterwarnings("ignore")

# Data source mode – set at startup via --source argument
DATA_SOURCE = "azure"   # overwritten in main


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


# Dataset loading – branches on DATA_SOURCE dpending if we are using the local CSV or Azure

def loadDatasetLocal() -> pd.DataFrame:
    """Load All_Diets.csv from local (same directory as this script)."""
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "All_Diets.csv")
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"All_Diets.csv not found at {local_path}")
    return pd.read_csv(local_path)


def loadDatasetAzure() -> pd.DataFrame:
    """Load All_Diets.csv from Azure Blob Storage."""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER", "data")
    blob_name = os.getenv("BLOB_FILE", "All_Diets.csv")

    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=blob_name,
    )

    stream = blob_client.download_blob()
    csv_bytes = stream.readall()
    return pd.read_csv(BytesIO(csv_bytes))


def loadDataset() -> pd.DataFrame:
    if DATA_SOURCE == "local":
        return loadDatasetLocal()
    return loadDatasetAzure()


# Static file routes

@app.get("/")
def home():
    return send_from_directory(".", "index.html")


@app.get("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.get("/style.css")
def style():
    return send_from_directory(".", "style.css")

# API routes

@app.get("/recipes")
@app.get("/recipies")
def recipes():
    """
    Returns a paginated list of recipes.

    Query params:
        dietType  – filter by diet type (optional)
        search    – case-insensitive substring match on Recipe_name (optional)
        page      – 1-based page number (default 1)
        limit     – rows per page (default 20)
    """
    try:
        dietType = whitelistInput(request.values.get("dietType"))
        search   = request.values.get("search", "").strip()

        try:
            page  = max(1, int(request.values.get("page",  1)))
            limit = max(1, int(request.values.get("limit", 20)))
        except ValueError:
            page, limit = 1, 20

        df = loadDataset()
        df = fixDataset(df)

        # filter
        if dietType:
            df = df.loc[df["Diet_type"].str.lower() == dietType]
        if search:
            df = df.loc[df["Recipe_name"].str.contains(search, case=False, na=False)]

        # select columns
        df = df[["Recipe_name", "Diet_type", "Cuisine_type", "Protein(g)", "Carbs(g)", "Fat(g)"]]

        total_count = len(df)
        total_pages = max(1, -(-total_count // limit))   # ceiling division
        page        = min(page, total_pages)

        start = (page - 1) * limit
        end   = start + limit
        page_df = df.iloc[start:end]

        return jsonify({
            "page":        page,
            "limit":       limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "data":        page_df.to_dict(orient="records"),
        }), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed to load dataset", "details": str(e)}), 500


@app.get("/insights")
def insights():
    """
    Returns protein-to-carbs and carbs-to-fat ratios per recipe.

    Query params:
        dietType – filter by diet type (optional)
    """
    try:
        dietType = whitelistInput(request.values.get("dietType"))

        df = loadDataset()
        df = fixDataset(df)

        if dietType:
            df = df.loc[df["Diet_type"].str.lower() == dietType]

        value = df[["Recipe_name", "Protein_to_Carbs_ratio", "Carbs_to_Fat_ratio"]]
        value = value.to_dict(orient="records")

        return jsonify(value), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed to load dataset", "details": str(e)}), 500


@app.get("/clusters")
def clusters():
    """Returns mean Protein / Carbs / Fat grouped by diet type."""
    try:
        df = loadDataset()
        df = fixDataset(df)

        value = df.groupby("Diet_type")[["Protein(g)", "Carbs(g)", "Fat(g)"]].mean()
        value = value.to_dict(orient="index")

        return jsonify(value), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed to load dataset", "details": str(e)}), 500


# Entry point


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nutritional Insights API")
    parser.add_argument(
        "--source",
        choices=["local", "azure"],
        default="azure",
        help="Data source: 'local' reads All_Diets.csv from disk; "
             "'azure' reads from Azure Blob Storage (default).",
    )
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default 5000)")
    args = parser.parse_args()

    DATA_SOURCE = args.source
    print(f"[startup] data source = {DATA_SOURCE}")

    app.run(host="0.0.0.0", port=args.port)
