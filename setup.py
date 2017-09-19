from setuptools import setup

setup(
    name="mt2414",
    description="MT2414",
    version="0.1.0",
    install_requires=[
        "nltk",
        "polib",
        "Flask",
        "Flask-RESTful",
        "PyJWT",
        "Flask-Cors",
        "requests",
        "psycopg2",
        "scrypt",
        "gunicorn",
        "pyexcel",
	"pyotp"
        ],
)
