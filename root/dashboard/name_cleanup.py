name_cleaner = {
    'emp_driver_id__raw_data_driver_id': 'NE_Driver_id',
    'net_reroute_freq': 'Net_Reroute_Freq',
    'dispatch_call_member_freq': 'AAA_Dispatch_Call_Member_Freq',
    'spp_call_member_freq': 'STATION_CALL_MEMBER_FREQ',
    'truck_call_member_freq': 'KMI_Driver_Contact',
    'long_ata_freq': 'Percent_Long_Ata',
    'response_sat_std12_e': 'Response_Time_Sat',
    'check_idpliant_freq': 'DO_NOT_USE_Check_ID_APP_USAGE_RATE',
    'check_idpliant_with_tablet_freq': 'CHECK_ID_APP_USAGE_RATE',
    'check_id_scan_freq': 'CHECK_ID_SCAN_RATE',
    'check_id_no_scan_reason_declined_scan_freq': 'DL_SCAN_DECLINE_RATE',
    'check_id_no_scan_reason_scan_failed_freq': 'DL_SCAN_FAIL_RATE',
    'check_id_decline_reason_no_valid_id_freq': 'NO_ID_PRESENTED',
    'check_id_alt_id_no_dl_count': 'NON_DL_ALT_ID_RATE_COUNT',
    'check_id_alt_id_no_dl_freq': 'NON_DL_ALT_ID_RATE_FREQ',
    'check_id_declined_reason_gone_on_arrival_freq': 'NO_ID_GONE_ON_ARRIVAL_RATE_FREQ',
    'check_id_declined_reason_gone_on_arrival_count': 'NO_ID_GONE_ON_ARRIVAL_RATE_COUNT',
    'check_id_declined_reason_no_name_match_freq': 'ID_NON_MATCH_RATE',
    'has_tablet_volume': 'TABLET_VOLUME',
    'facility_sat_std12_e': 'Service_Vehicle_SAT',
    'kept_informed_sat_std12_e': 'KMI_SAT',
    'request_service_sat_std12_e': 'Requesting_Service_Sat',
    'volume': 'Volume',
    'tow_volume': 'Tow_Volume',
    'battery_volume': 'Battery_Volume',
    'not_tow_volume': 'Battery_Plus_Light_SVC',
    "aaa_mgmt_any_facility_sat_avg": "Driver_Sat",
    "aaa_mgmt_any_overall_sat_avg": "Overall_Sat",
    "aaa_mgmt_any_kept_informed_sat_avg": "Kept_Informed_Sat",
    "aaa_mgmt_any_response_sat_avg": "Response_Sat",
    "aaa_mgmt_any_request_service_sat_avg": "Request_Service_Sat",
    "aaa_mgmt_any_facility_sat_count": "Driver_Sat_Base_Size",
    "aaa_mgmt_any_kept_informed_sat_count": "Kept_Informed_Base_Size",
    "aaa_mgmt_any_response_sat_count": "Response_Sat_Base_Size",
    "aaa_mgmt_any_request_service_sat_count": "Request_Service_Sat_Base_Size",
    "aaa_mgmt_any_overall_sat_count": "Overall_Sat_Base_Size",
    "passed_calls_freq_3m": "Passed_Calls_Freq_by_3_Month_Comp_Period",
    "passed_calls_freq": "Passed_Calls_Freq_by_Month",
    "aaa_mgmt_tow_facility_sat_avg": "Driver_Sat_(Tow)",
    "aaa_mgmt_tow_overall_sat_avg": "Overall_Sat_(Tow)",
    "aaa_mgmt_tow_kept_informed_sat_avg": "Kept_Informed_Sat_(Tow)",
    "aaa_mgmt_tow_response_sat_avg": "Response_Sat_(Tow)",
    "aaa_mgmt_tow_request_service_sat_avg": "Request_Service_Sat_(Tow)",
    "aaa_mgmt_tow_facility_sat_count": "Driver_Sat_Base_Size_(Tow)",
    "aaa_mgmt_tow_kept_informed_sat_count": "Kept_Informed_Base_Size_(Tow)",
    "aaa_mgmt_tow_response_sat_count": "Response_Sat_Base_Size_(Tow)",
    "aaa_mgmt_tow_request_service_sat_count": "Request_Service_Sat_Base_Size_(Tow)",
    "aaa_mgmt_tow_overall_sat_count": "Overall_Sat_Base_Size_(Tow)",

    "aaa_mgmt_not_tow_facility_sat_avg": "Driver_Sat_(Light_Service)",
    "aaa_mgmt_not_tow_overall_sat_avg": "Overall_Sat_(Light_Service)",
    "aaa_mgmt_not_tow_kept_informed_sat_avg": "Kept_Informed_Sat_(Light_Service)",
    "aaa_mgmt_not_tow_response_sat_avg": "Response_Sat_(Light_Service)",
    "aaa_mgmt_not_tow_request_service_sat_avg": "Request_Service_Sat_(Light_Service)",
    "aaa_mgmt_not_tow_facility_sat_count": "Driver_Sat_Base_Size_(Light_Service)",
    "aaa_mgmt_not_tow_kept_informed_sat_count": "Kept_Informed_Base_Size__(Light_Service)",
    "aaa_mgmt_not_tow_response_sat_count": "Response_Sat_Base_Size_(Light_Service)",
    "aaa_mgmt_not_tow_request_service_sat_count": "Request_Service_Sat_Base_Size_(Light_Service)",
    "aaa_mgmt_not_tow_overall_sat_count": "Overall_Sat_Base_Size_(Light_Service)",

    "aaa_mgmt_battery_facility_sat_avg": "Driver_Sat_(Battery)",
    "aaa_mgmt_battery_overall_sat_avg": "Overall_Sat_(Battery)",
    "aaa_mgmt_battery_kept_informed_sat_avg": "Kept_Informed_Sat_(Battery)",
    "aaa_mgmt_battery_response_sat_avg": "Response_Sat_(Battery)",
    "aaa_mgmt_battery_request_service_sat_avg": "Request_Service_Sat_(Battery)",
    "aaa_mgmt_battery_facility_sat_count": "Driver_Sat_Base_Size_(Battery)",
    "aaa_mgmt_battery_kept_informed_sat_count": "Kept_Informed_Base_Size_(Battery)",
    "aaa_mgmt_battery_response_sat_count": "Response_Sat_Base_Size_(Battery)",
    "aaa_mgmt_battery_request_service_sat_count": "Request_Service_Sat_Base_Size_(Battery)",
    "aaa_mgmt_battery_overall_sat_count": "Overall_Sat_Base_Size_(Battery)",

    "comp_any_facility_sat_avg": "Driver_Sat",
    "comp_any_overall_sat_avg": "Overall_Sat",
    "comp_any_kept_informed_sat_avg": "Kept_Informed_Sat",
    "comp_any_response_sat_avg": "Response_Sat",
    "comp_any_request_service_sat_avg": "Request_Service_Sat",
    "comp_any_facility_sat_count": "Driver_Sat_Base_Size",
    "comp_any_kept_informed_sat_count": "Kept_Informed_Base_Size",
    "comp_any_response_sat_count": "Response_Sat_Base_Size",
    "comp_any_request_service_sat_count": "Request_Service_Sat_Base_Size",
    "comp_any_overall_sat_count": "Overall_Sat_Base_Size",

    "comp_tow_facility_sat_avg": "Driver_Sat_(Tow)",
    "comp_tow_overall_sat_avg": "Overall_Sat_(Tow)",
    "comp_tow_kept_informed_sat_avg": "Kept_Informed_Sat_(Tow)",
    "comp_tow_response_sat_avg": "Response_Sat_(Tow)",
    "comp_tow_request_service_sat_avg": "Request_Service_Sat_(Tow)",
    "comp_tow_facility_sat_count": "Driver_Sat_Base_Size_(Tow)",
    "comp_tow_kept_informed_sat_count": "Kept_Informed_Base_Size_(Tow)",
    "comp_tow_response_sat_count": "Response_Sat_Base_Size_(Tow)",
    "comp_tow_request_service_sat_count": "Request_Service_Sat_Base_Size_(Tow)",
    "comp_tow_overall_sat_count": "Overall_Sat_Base_Size_(Tow)",

    "comp_not_tow_facility_sat_avg": "Driver_Sat_(Light_Service)",
    "comp_not_tow_overall_sat_avg": "Overall_Sat_(Light_Service)",
    "comp_not_tow_kept_informed_sat_avg": "Kept_Informed_Sat_(Light_Service)",
    "comp_not_tow_response_sat_avg": "Response_Sat_(Light_Service)",
    "comp_not_tow_request_service_sat_avg": "Request_Service_Sat_(Light_Service)",
    "comp_not_tow_facility_sat_count": "Driver_Sat_Base_Size_(Light_Service)",
    "comp_not_tow_kept_informed_sat_count": "Kept_Informed_Base_Size__(Light_Service)",
    "comp_not_tow_response_sat_count": "Response_Sat_Base_Size_(Light_Service)",
    "comp_not_tow_request_service_sat_count": "Request_Service_Sat_Base_Size_(Light_Service)",
    "comp_not_tow_overall_sat_count": "Overall_Sat_Base_Size_(Light_Service)",

    "comp_battery_facility_sat_avg": "Driver_Sat_(Battery)",
    "comp_battery_overall_sat_avg": "Overall_Sat_(Battery)",
    "comp_battery_kept_informed_sat_avg": "Kept_Informed_Sat_(Battery)",
    "comp_battery_response_sat_avg": "Response_Sat_(Battery)",
    "comp_battery_request_service_sat_avg": "Request_Service_Sat_(Battery)",
    "comp_battery_facility_sat_count": "Driver_Sat_Base_Size_(Battery)",
    "comp_battery_kept_informed_sat_count": "Kept_Informed_Base_Size_(Battery)",
    "comp_battery_response_sat_count": "Response_Sat_Base_Size_(Battery)",
    "comp_battery_request_service_sat_count": "Request_Service_Sat_Base_Size_(Battery)",
    "comp_battery_overall_sat_count": "Overall_Sat_Base_Size_(Battery)",

    "duplicate_freq": "Duplicate_Frequency",
    "lost_call_freq": "Lost_Call_Frequency",

    "overall_sat_avg": "Overall_Satisfaction",
    "overall_sat_count": "Survey_Count",
    "facility_sat_avg": "Service_Vehicle_Driver",
    "response_sat_avg": "Response_Time",
    "kept_informed_sat_avg": "Keeping_Members_Informed",

    'outc1': 'overall_satisfaction',
    'driver10': 'driver_sat',
    'q24': 'response_time',
    'q26': 'kept_informed',
    'driver5': 'requesting_service',
    'q30': 'member_comments',

    'sc_dt_surveys': 'service_date',
    'sc_id_surveys': 'call_id',
    'org_svc_facl_id__name': 'facility_id',
    'org_business_id__name': 'facility_name',
    'emp_driver_id__full_name': 'driver',

    'recordeddate': "Recorded_date",

    'survey__appeals_eligible': 'appeals_eligible',
    'survey__appeals_status': 'appeals_status',
    'survey__driver10': 'driver_sat',
    'survey__id': 'survey_id',
    'survey__outc1': 'overall_sat',


    'resolution_desc': 'service_resolution',

    'pta': 'Promised_Time_of_Arrival_(minutes)',
    'ata': 'Actual_Time_of_Arrival_(minutes)',
    'ata_minus_pta': 'ATA_-_PTA',
    'driver_called': 'Driver_Called',
    'spot_minutes': 'Spot_Minutes',
    'fst_shop': 'first_spot_fac',
    'dispatch_communicated': 'Dispatc_communicated_(by_any_means)',
    'call_center_operator': 'Call_Center_Operator',
    'tcd': 'trouble_code',
    're_tm': 'Call_Received_Time',
    'first_spot_fac': 'First_Facility_Spotted_the_call',
    'check_idpliant': 'Used_Check_ID_App',
    'date_updated_surveys': 'Recorded_Date',


}
