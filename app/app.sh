#!/usr/bin/env bash

pip install -r requirements.txt --user
solara run domino_cost.py --host 0.0.0.0 --port 8888
