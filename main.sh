#!/bin/bash
# Generates the Top 10 trending places on OSM (with a 2 day lag)

# bail out in case of errors
set -e

date_fmt="${DATE_FMT:--u -Iseconds}"

exec >$(date +%Y%m%d%H%M%S).log 2>&1

tile_log_diff="2"
date_diff="7"

date_to=$(date "--date=-${tile_log_diff} day" +%Y-%m-%d)
date_from=$(date "--date=${date_to} -${date_diff} day+1 day" +%Y-%m-%d)

output_dir="$(readlink -e ${OUTPUT_DIR:-.})/"
mkdir -p $output_dir

logged_cmd()
{
  echo "$(date $date_fmt): Executing [$@]"
  sh -c -e "$@"
  echo "$(date $date_fmt): Done"
}

_errcode=0
_exitprocmsg="FAILED previous step, aborting with exitcode"

exitprocINT()
{
  _errcode=$?
  exitproc "INT"
}
exitprocHUP()
{
  _errcode=$?
  exitproc "HUP"
}
exitprocTERM()
{
  _errcode=$?
  exitproc "TERM"
}
exitprocKILL()
{
  _errcode=$?
  exitproc "KILL"
}
exitprocEXIT()
{
  _errcode=$?
  exitproc "EXIT"
}

exitproc()
{
  locSigName=${1:-4};
  printf "%s: got SIG%s; %s %s\n" "$(date $date_fmt)" "${locSigName}" "$_exitprocmsg" "$_errcode"
  exit $_errcode;
}

trap exitprocINT INT
trap exitprocHUP HUP
trap exitprocTERM TERM
trap exitprocKILL KILL
trap exitprocEXIT EXIT

logged_cmd "python3 Fetch2.py --date_from=$date_from --date_to=$date_to >${output_dir}Trends.csv"
logged_cmd "test -r ${output_dir}Trends.csv && cat ${output_dir}Trends.csv | python3 Bubble.py --date_precision=1d --min_zoom=10 --max_zoom=19 --min_subz=10 --max_subz=10 --no_per_day >${output_dir}Zoom10Tiles.csv"
logged_cmd "test -r ${output_dir}Zoom10Tiles.csv && cat ${output_dir}Zoom10Tiles.csv | python3 Top_Trending.py --graph --date=$date_to"
logged_cmd "python3 Trending_Bot.py"
_exitprocmsg="SUCCESS, program terminated with exitcode"

