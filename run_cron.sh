#!/bin/bash

# prepend the environment variables to the crontab
env | cat - crons.conf > cron2.conf

# add the cronfile
crontab cron2.conf

# Run cron daemon
cron -f