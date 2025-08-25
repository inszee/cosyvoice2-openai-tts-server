#!/bin/bash
source /root/miniforge3/etc/profile.d/conda.sh
conda activate cosyvoice
nohup bash -C ./start_server.sh > output.log 2>&1 && echo "Application finished." &