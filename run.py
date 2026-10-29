from app import create_app

# Instantiate the Flask app using the factory function
app = create_app()

if __name__ == "__main__":
    # Run the development server
    # debug=True automatically reloads on code changes
    app.run(host="127.0.0.1", port=5000, debug=True)

