#!/bin/bash

function run_flake8() {
    pip install flake8
    flake8 .
    if [[ ! $? == 0 ]]; then
        exit 1
    fi
}

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv local 3.6.5 3.7.0
    pyenv global 3.7.0
    run_flake8
    tox
else
    run_flake8
    pytest tests --cov=repobee_csvgrades --cov-branch
fi
