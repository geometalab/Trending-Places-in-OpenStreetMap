#!/bin/bash
# Generates the Top 10 trending places on OSM (with a 2 day lag)

# bail out in case of errors
set -e

exec >$(date +%Y%m%d%H%M%S).log 2>&1

tile_log_diff="2"
date_diff="7"

date_to=$(date "--date=-${tile_log_diff} day" +%Y-%m-%d)
date_from=$(date "--date=${date_to} -${date_diff} day+1 day" +%Y-%m-%d)
min_zoom=${MIN_ZOOM:-10}
max_zoom=${MAX_ZOOM:-19}
min_cache_zoom=${MIN_CACHE_ZOOM:-$min_zoom}

output_dir="$(readlink -e ${OUTPUT_DIR:-.})/"
mkdir -p $output_dir

logged_cmd()
{
	echo "$(date +%Y%m%d%H%M%S): Executing [$@]"
	sh -c +e "$@"
	echo "$(date +%Y%m%d%H%M%S): Done"
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
	printf "%s: got SIG%s; %s %s\n" "$(date +%Y%m%d%H%M%S)" "${locSigName}" "$_exitprocmsg" "$_errcode"
	exit $_errcode;
}

trap exitprocINT INT
trap exitprocHUP HUP
trap exitprocTERM TERM
trap exitprocKILL KILL
trap exitprocEXIT EXIT

logged_cmd "python3 Fetch2.py --date_from=$date_from --date_to=$date_to --min_zoom=$min_zoom --max_zoom=$max_zoom --min_cache_zoom=$min_cache_zoom >${output_dir}Trends.csv"
logged_cmd "test -r ${output_dir}Trends.csv && cat ${output_dir}Trends.csv | python3 Bubble.py --date_precision=1d --min_zoom=$min_zoom --max_zoom=$max_zoom --min_subz=$min_zoom --max_subz=$min_zoom --no_per_day >${output_dir}Zoom10Tiles.csv"
logged_cmd "test -r ${output_dir}Zoom10Tiles.csv && cat ${output_dir}Zoom10Tiles.csv | python3 Top_Trending.py --graph --date=$date_to"
logged_cmd "python3 Trending_Bot.py"
_exitprocmsg="SUCCESS, program terminated with exitcode"

