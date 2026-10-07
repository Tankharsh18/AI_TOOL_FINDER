import os

from flask import Flask, session, request, render_template, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "student-project-secret-key")

# Database connection
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password=os.getenv("DB_PASSWORD"),
    database='ai_tools_db'
)
cursor = conn.cursor(dictionary=True)

# Constants
TOOLS_PER_PAGE = 9

CATEGORY_ICONS = {
    "Coding": ("/static/coding.png", "#dbeafe"),
    "Developer": ("/static/dev.png", "#dbeafe"),
    "Writing": ("/static/writing.png", "#fce7f3"),
    "Productivity": ("/static/cal.png", "#e0f2fe"),
    "Search": ("/static/search.png", "#f0fdf4"),
    "Chatbot": ("/static/chatbot.png", "#d1fae5"),
    "Marketing": ("/static/marketing.png", "#fef3c7"),
    "SEO": ("/static/seo.png", "#dcfce7"),
    "Translation": ("/static/translation.png", "#e0e7ff"),
    "Voice": ("/static/voice.png", "#ede9fe"),
    "Audio": ("/static/audio.png", "#f0f9ff"),
    "Music": ("/static/music.png", "#ecfeff"),
    "Image Generation": ("/static/imagegen.png", "#ede9fe"),
    "Design": ("/static/design.png", "#fdf4ff"),
    "Video Generation": ("/static/videogen.png", "#fee2e2"),
    "Animation": ("/static/animation.png", "#fef9c3"),
}

# Helpers
def is_logged_in():
    return "logged_in" in session

def enrich(tools):
    """Add icon/icon_bg from category and normalise pricing."""
    for t in tools:
        icon, bg = CATEGORY_ICONS.get(t.get("category", ""), ("static/coding.png", "#f1f5f9"))
        t["icon"]    = icon
        t["icon_bg"] = bg
        if not t.get("pricing"):
            t["pricing"] = "Free"
    return tools

def get_all_categories():
    """Return categories with tool counts and icons, sorted by count."""
    cursor.execute("""
        SELECT category, COUNT(*) AS tool_count
        FROM ai_tools
        GROUP BY category
        ORDER BY tool_count DESC
    """)
    rows = cursor.fetchall()
    for r in rows:
        icon, bg = CATEGORY_ICONS.get(r["category"], ("static/coding.png", "#f1f5f9"))
        r["icon"]    = icon
        r["icon_bg"] = bg
    return rows

# Default
@app.route("/")
def default():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if is_logged_in():
        return redirect(url_for("index"))

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        # Check email
        cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))

        # Check username
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash("That username is already taken.", "danger")
            return redirect(url_for("register"))

        # Insert user
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()

        flash("Account created! You can now sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session["logged_in"] = True
            session["username"]  = user["username"]
            flash(f"Welcome back, {user['username']}! 👋", "success")
            return redirect(url_for("index"))

        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "info")
    return redirect(url_for("login"))

# Index / Home
@app.route("/index")
def index():
    if not is_logged_in():
        return redirect(url_for("login"))

    # Total tool count
    cursor.execute("SELECT COUNT(*) AS total FROM ai_tools")
    total_tools = cursor.fetchone()["total"]

    # Free tool count
    cursor.execute("SELECT COUNT(*) AS cnt FROM ai_tools WHERE pricing LIKE %s OR pricing IS NULL", ("%Free%",))
    free_count = cursor.fetchone()["cnt"]

    # All categories with counts + icons
    all_categories = get_all_categories()

    # Top 5 categories for hero quick-links
    top_categories = all_categories[:5]

    # 8 most recently added tools
    cursor.execute("""
        SELECT name, description, category, url, pricing,logo
        FROM ai_tools
        where name IN ('chatgpt','claude','gemini','replit ai','cursor')
    """)


    # ORDER BY created_at DESC
            # LIMIT 3
    recent_tools = enrich(cursor.fetchall())

    return render_template(
        "index.html",
        username       = session.get("username"),
        total_tools    = total_tools,
        free_count     = free_count,
        total_categories = len(all_categories),
        all_categories = all_categories,
        top_categories = top_categories,
        recent_tools   = recent_tools,
    )

# Category browser
@app.route("/category")
def category():
    if not is_logged_in():
        return redirect(url_for("login"))

    categories = get_all_categories()

    return render_template(
        "category.html",
        username   = session.get("username"),
        categories = categories,
    )

# Search — filters · sort · pagination
@app.route("/search")
def search():
    if not is_logged_in():
        return redirect(url_for("login"))

    query           = request.args.get("query",    "").strip()
    active_category = request.args.get("category", "").strip()
    active_pricing  = request.args.get("pricing",  "").strip()
    active_sort     = request.args.get("sort",     "newest").strip()
    try:
        current_page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        current_page = 1

    conditions, params = [], []
    
    if query:
        conditions.append(
            "(name LIKE %s OR description LIKE %s OR tags LIKE %s OR category LIKE %s)"
        )
        like = f"%{query}%"
        params += [like, like, like, like]

    if active_category:
        conditions.append("category = %s")
        params.append(active_category)

    if active_pricing == "Free":
        conditions.append("(pricing IS NULL OR pricing LIKE %s)")
        params.append("%Free%")
    elif active_pricing == "Paid":
        conditions.append("pricing IS NOT NULL AND pricing NOT LIKE %s")
        params.append("%Free%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    order_map = {
        "newest": "created_at DESC",
        "oldest": "created_at ASC",
        "name":   "name ASC",
    }
    order = "ORDER BY " + order_map.get(active_sort, "created_at DESC")

    cursor.execute(f"SELECT COUNT(*) AS total FROM ai_tools {where}", params)
    total_results = cursor.fetchone()["total"]

    total_pages  = max(1, -(-total_results // TOOLS_PER_PAGE))
    current_page = min(current_page, total_pages)
    offset       = (current_page - 1) * TOOLS_PER_PAGE

    cursor.execute(
        f"""SELECT name, description, category, url, tags, pricing, created_at,logo
            FROM ai_tools {where} {order}
            LIMIT %s OFFSET %s""",
        params + [TOOLS_PER_PAGE, offset]
    )
    results = enrich(cursor.fetchall())

    cursor.execute("SELECT DISTINCT category FROM ai_tools ORDER BY category")
    all_categories = [r["category"] for r in cursor.fetchall()]

    return render_template(
        "search.html",
        username        = session.get("username"),
        query           = query,
        results         = results,
        active_category = active_category,
        active_pricing  = active_pricing,
        active_sort     = active_sort,
        current_page    = current_page,
        total_pages     = total_pages,
        total_results   = total_results,
        all_categories  = all_categories,
    )

# Cache-control — prevent back after logout
@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"]        = "no-cache"
    response.headers["Expires"]       = "0"
    return response

if __name__ == "__main__":
    app.run(debug=True)
