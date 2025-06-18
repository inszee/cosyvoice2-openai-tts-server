#!/bin/bash

nohup bash -C ./start_server.sh > output.log 2>&1 && echo "Application finished." &