
from pathlib import Path

import pandas as pd
import pm4py
import json

def discover_dfg(df: pd.DataFrame) -> dict:
    """
    Discover a Directly-Follows Graph (DFG) from wallet events.

    Returns the original JSON-serializable dictionary containing:
    - edges
    - start_activities
    - end_activities

    Also exports:
    - dfg.png: original DFG
    - dfg_filtered.png: filtered DFG
    """

    if df.empty:
        return {
            "edges": [],
            "start_activities": {},
            "end_activities": {},
        }

    df = df.copy()

    # Prepare PM4Py event log columns.
    df["case:concept:name"] = df["wallet_address"]
    df["concept:name"] = df["action"]
    df["time:timestamp"] = pd.to_datetime(
        df["event_time"],
        utc=True,
    )

    # Sort events chronologically within each wallet.
    df = df.sort_values(
        ["case:concept:name", "time:timestamp"],
        kind="stable",
    )

    # Discover the original DFG.
    dfg, start_activities, end_activities = pm4py.discover_dfg(
        df,
        case_id_key="case:concept:name",
        activity_key="concept:name",
        timestamp_key="time:timestamp",
    )

    # Export the original visualization.
    output_path = Path("dfg.png")

    pm4py.save_vis_dfg(
        dfg,
        start_activities,
        end_activities,
        str(output_path),
    )

    # Preserve the original JSON output.
    edges = [
        {
            "source": source,
            "target": target,
            "count": int(count),
        }
        for (source, target), count in dfg.items()
    ]

    start_activities_result = {
        str(activity): int(count)
        for activity, count in start_activities.items()
    }

    end_activities_result = {
        str(activity): int(count)
        for activity, count in end_activities.items()
    }

    # --------------------------------------------------
    # Filtered DFG visualization only.
    # The original DFG and JSON output remain unchanged.
    # --------------------------------------------------

    # 1. Exclude only the specified activities.
    #    Exact matching preserves activities such as:
    #    transfer_native
    #    transfer_target_token
    excluded_activities = {
        "create_account",
        "create_token_account",
        "transfer",
        "swap",
        "unknown",
        "receive_non_target_token",
        "transfer_non_target_token",
    }

    filtered_dfg = {
        (source, target): count
        for (source, target), count in dfg.items()
        if count >= 5
        and source not in excluded_activities
        and target not in excluded_activities
    }

    # 2. Keep start/end activities that remain visible.
    visible_activities = {
        activity
        for source, target in filtered_dfg
        for activity in (source, target)
    }

    filtered_starts = {
        activity: count
        for activity, count in start_activities.items()
        if activity in visible_activities
    }

    filtered_ends = {
        activity: count
        for activity, count in end_activities.items()
        if activity in visible_activities
    }

    # 3. Export the filtered visualization.
    filtered_output_path = Path("dfg_filtered.png")

    if filtered_dfg:
        pm4py.save_vis_dfg(
            filtered_dfg,
            filtered_starts,
            filtered_ends,
            str(filtered_output_path),
        )

        print(f"Original DFG saved to: {output_path}")
        print(f"Filtered DFG saved to: {filtered_output_path}")
    else:
        print("No edges remain after filtering.")

    # 4. Print filtering statistics.
    original_activities = (
        set(start_activities)
        | set(end_activities)
    )

    original_activities.update(
        activity
        for source, target in dfg
        for activity in (source, target)
    )

    print(f"Original nodes: {len(original_activities)}")
    print(f"Visible nodes: {len(visible_activities)}")
    print(f"Original edges: {len(dfg)}")
    print(f"Filtered edges: {len(filtered_dfg)}")
    print(f"Excluded activities: {sorted(excluded_activities)}")

    # 5. Debug: check whether the desired nodes survived.
    desired_activities = {
        "transfer_native",
        "transfer_target_token",
    }

    print("\nDesired activity status:")

    for activity in sorted(desired_activities):
        exists_in_original = activity in original_activities
        exists_in_filtered = activity in visible_activities

        print(
            f"  {activity}: "
            f"original={exists_in_original}, "
            f"filtered={exists_in_filtered}"
        )

        if exists_in_original and not exists_in_filtered:
            print(
                f"    No remaining edges connect to {activity} "
                "after exclusion."
            )

    

    # Export filtered DFG as JSON.
    filtered_json = {
        "edges": [
            {
                "source": source,
                "target": target,
                "count": int(count),
            }
            for (source, target), count in filtered_dfg.items()
        ],
        "start_activities": {
            str(activity): int(count)
            for activity, count in filtered_starts.items()
        },
        "end_activities": {
            str(activity): int(count)
            for activity, count in filtered_ends.items()
        },
    }

    filtered_json_path = Path("dfg_filtered.json")

    with filtered_json_path.open("w", encoding="utf-8") as f:
        json.dump(
            filtered_json,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Filtered DFG JSON saved to: {filtered_json_path}")
    # Return both graph variants so the dashboard can render them directly.
    # Keep the original raw DFG shape backward-compatible.
    return {
        "edges": edges,
        "start_activities": start_activities_result,
        "end_activities": end_activities_result,
        "filtered_dfg": filtered_json,
        "filtering_statistics": {
            "original_edge_count": len(edges),
            "filtered_edge_count": len(filtered_json["edges"]),
            "min_edge_count": 5,
            "excluded_activities": sorted(excluded_activities),
        },
    }


