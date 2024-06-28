from flask import Flask, render_template, request, redirect, url_for
import os
import logging
import re

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello'

if __name__ == '__main__':
    app.run(debug=True)
