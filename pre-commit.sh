#!/bin/bash

source .venv/bin/activate
jupytext --sync *.ipynb

deactivate