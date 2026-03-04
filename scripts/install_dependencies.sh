#!/bin/bash

# Install dependencies for the project
echo "Installing dependencies..."

sudo apt-get install ninja-build

conda create -n pytracking python=3.7
conda activate pytracking

pip install torch torchvision torchaudio

pip install numpy matplotlib pandas tqdm opencv-python tb visdom scikit-image tikzplotlib gdown cython pycocotools lvis jpeg4py PyYAML

