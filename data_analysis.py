import argparse
import os
import warnings

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for, g
from flask_cors import CORS
from dotenv import load_dotenv

from auth import auth0
from auth0_server_python.auth_server.server_client import StartInteractiveLoginOptions

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

app.secret_key = os.getenv("AUTH0_SECRET")

# Secure session cookie settings (HTTPS not yet active so SECURE=False for dev)
app.config.update(
    SESSION_COOKIE_SECURE=False,   # Set True when HTTPS is enabled
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────
# Auth0 request context helper
# ──────────────────────────────────────────────

@app.before_request
def store_request_context():
    """Make the current request available to the Auth0 SDK."""
    g.store_options = {"request": request}


# ──────────────────────────────────────────────
# Dataset helpers
# ──────────────────────────────────────────────

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


def loadDatasetLocal() -> pd.DataFrame:
    """Load All_Diets.csv from the same directory as this script."""
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "All_Diets.csv")
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"All_Diets.csv not found at {local_path}")
    return pd.read_csv(local_path)


def loadDataset() -> pd.DataFrame:
    """Always load the dataset from the local CSV file."""
    return loadDatasetLocal()


# ──────────────────────────────────────────────
# Static asset routes
# ──────────────────────────────────────────────

@app.get("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.get("/style.css")
def style():
    return send_from_directory(".", "style.css")


# ──────────────────────────────────────────────
# Main dashboard
# ──────────────────────────────────────────────

@app.get("/")
async def home():
    """Home page – renders the dashboard, passing auth user info if logged in."""
    user = await auth0.get_user(g.store_options)
    return render_template("index.html", user=user)


# ──────────────────────────────────────────────
# Auth0 OAuth routes
# ──────────────────────────────────────────────

@app.get("/login")
async def login():
    """
    Start the Auth0 interactive login flow.
    An optional ?connection=<provider> query param (google-oauth2 or github)
    pre-selects the social provider on the Auth0 Universal Login page.
    """
    connection = request.args.get("connection")
    options = StartInteractiveLoginOptions(
        authorization_params={"connection": connection} if connection else None
    )
    authorization_url = await auth0.start_interactive_login(options, g.store_options)
    return redirect(authorization_url)


@app.get("/callback")
async def callback():
    """Handle the OAuth callback from Auth0 after the user authenticates."""
    try:
        await auth0.complete_interactive_login(str(request.url), g.store_options)
        return redirect(url_for("home"))
    except Exception as e:
        return f"Authentication error: {str(e)}", 400


@app.get("/profile")
async def profile():
    """
    Protected page – requires an active Auth0 session.
    Redirects to /login if the user is not authenticated.
    """
    user = await auth0.get_user(g.store_options)

    if not user:
        return redirect(url_for("login"))

    return render_template("profile.html", user=user)


@app.get("/logout")
async def logout():
    """Clear the Auth0 session and redirect to the Auth0 logout endpoint."""
    logout_url = await auth0.logout(None, g.store_options)
    return redirect(logout_url)


# ──────────────────────────────────────────────
# API routes
# ──────────────────────────────────────────────

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
        search = request.values.get("search", "").strip()

        try:
            page = max(1, int(request.values.get("page", 1)))
            limit = max(1, int(request.values.get("limit", 20)))
        except ValueError:
            page, limit = 1, 20

        df = loadDataset()
        df = fixDataset(df)

        if dietType:
            df = df.loc[df["Diet_type"].str.lower() == dietType]
        if search:
            df = df.loc[df["Recipe_name"].str.contains(search, case=False, na=False)]

        df = df[["Recipe_name", "Diet_type", "Cuisine_type", "Protein(g)", "Carbs(g)", "Fat(g)"]]

        total_count = len(df)
        total_pages = max(1, -(-total_count // limit))
        page = min(page, total_pages)

        start = (page - 1) * limit
        end = start + limit
        page_df = df.iloc[start:end]

        return jsonify({
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "data": page_df.to_dict(orient="records"),
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


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nutritional Insights API")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default 5000)")
    args = parser.parse_args()

    print("[startup] data source = local CSV")

    app.run(host="0.0.0.0", port=args.port)