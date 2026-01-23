from flask import Flask
import solara.server.flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'

# Register Solara under "/solara_app/" (not "/")
app.register_blueprint(solara.server.flask.blueprint, url_prefix="/solara_app/")

# Set Solara's base path to match the URL prefix
solara.server.kernel_context.base_path = "/solara_app/"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)  # Listen on all interfaces