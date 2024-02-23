#!/usr/bin/env python3

from collections import defaultdict as dd
from datetime import timedelta as td
import json
import os
import sys
from statistics import mean, median

import requests
from box import Box

cores_uri = "https://api.spacexdata.com/v4/cores"
launches_uri = "https://api.spacexdata.com/v5/launches"


class JSObject:
    def __init__(self, obj):
        self._o = obj

    def __getattr__(self, item):
        return self._o


def get_cached(uri, pathname):
    if not os.path.exists(pathname):
        r = requests.get(uri)
        if r.status_code == 200:
            with open(pathname, "wb") as fw:
                fw.write(r.content)
        else:
            raise Exception(f"Can't access {uri}")
    with open(pathname, "rb") as fr:
        return Box({"list": json.loads(fr.read())})


def main():
    cores = dict()
    for core in get_cached(cores_uri, "cores.json").list:
        cores[core.id] = core

    launches = dd(list)
    launches_count = 0
    for launch in get_cached(launches_uri, "launches.json").list:
        launches_count += 1
        for core in launch.cores:
            launches[core.core].append(launch)

    ivals = dd(list)
    single_launch_core_count = 0
    multi_launch_core_count = 0
    z_launch_core_count = 0
    else_launch_core_count = 0
    min_ldate = sys.maxsize
    max_ldate = -sys.maxsize
    for core_id, core in cores.items():
        prev = None
        launch_count = len(launches[core_id])
        if launch_count == 0:
            z_launch_core_count += 1
        elif launch_count == 1:
            single_launch_core_count += 1
        elif launch_count > 1:
            multi_launch_core_count += 1
        else:
            else_launch_core_count += 1
        for launch in sorted(launches[core_id], key=lambda l: l.date_unix):
            min_ldate = min(launch.date_unix, min_ldate)
            max_ldate = max(launch.date_unix, max_ldate)
            if prev:
               ivals[core_id].append(Box(
                    timedelta=launch.date_unix - prev.date_unix,
                    this=launch,
                    prev=prev,
               ))
            prev = launch

    core_stats = Box()
    for core_id, ivals in ivals.items():
        core_stats[core_id] = {
            "avg": td(seconds=mean(ival.timedelta for ival in ivals)),
            "max": td(seconds=max(ival.timedelta for ival in ivals)),
            "min": td(seconds=min(ival.timedelta for ival in ivals)),
            "med": td(seconds=median(ival.timedelta for ival in ivals)),
            "num": len(ivals),
            "core_id": core_id,
        }

    ival_avg = mean(ival.timedelta for ival in ivals)
    ival_max = max(ival.timedelta for ival in ivals)
    ival_min = min(ival.timedelta for ival in ivals)
    ival_med = median(ival.timedelta for ival in ivals)

    print(f"Overall:\n"
          f"\tAverage:\t{td(seconds=ival_avg)}\n"
          f"\tMaximum:\t{td(seconds=ival_max)}"
          f"\n\tMinimum:\t{td(seconds=ival_min)}\n"
          f"\tMedian:\t{td(seconds=ival_med)}"
    )

    lcount = 0
    for stats in sorted(core_stats.values(), key=lambda s: s.min):
        print(f"Core: {cores[stats.core_id].serial}, "
              f"min: {stats.min}, "
              f"max: {stats.max}, "
              f"avg: {stats.avg}, "
              f"med: {stats.med}, "
              f"num: {stats.num}"
        )
        lcount += stats.num

    print(f"single-launch core count: {single_launch_core_count}\n"
          f"Multiple launch core count: {multi_launch_core_count}\n"
          f"Zero launch core count: {z_launch_core_count}\n"
          f"else core count: {else_launch_core_count}\n"
          f"launched core count:  {lcount}\n"
    )
    print(f"Core count: {len(cores)}\n"
          f"Launch count: {launches_count}\n"
          f"Min ldate: {min_ldate}\n"
          f"Max ldate: {max_ldate}")

    x = 1


if __name__ == '__main__':
    main()
