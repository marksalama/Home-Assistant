# Error diagnosis workflow

1. Start with `get_overview` to see pending updates, integration failures, and
   recent system-log volume.
2. Use `get_error_log`; it returns structured `system_log/list` entries with
   `level`, `name`, `message`, `source`, `count`, `first_occurred`, and optional
   `exception`.
3. For one entity, use `diagnose_entity`, then `get_history` or `get_logbook`.
4. For automation problems, use `list_automation_traces` and then
   `get_automation_trace` for the failed run.
5. For add-ons or HA OS problems, use `get_core_logs`, `get_supervisor_logs`,
   `get_addon_logs`, `supervisor_info`, and `host_info`.
6. Before changing YAML, read the file, snapshot automatically through the file
   tool, run `check_config`, then reload the domain or restart only after a
   valid config check.
