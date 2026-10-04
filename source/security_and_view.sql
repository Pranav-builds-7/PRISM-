-- Create a dedicated account that owns the view's execution context
CREATE USER IF NOT EXISTS 'prism_view_owner'@'%'
IDENTIFIED BY 'AgentPassword2026!';

Allow the view owner to read only the raw logistics table
GRANT SELECT
ON logistics.TBL_SC_FLEET_HIST_RAW
TO 'prism_view_owner'@'%';

-- Create the view with a restricted definer
CREATE OR REPLACE
DEFINER = 'prism_view_owner'@'%'
SQL SECURITY DEFINER
VIEW FDE_VIEWS.VW_ACTIVE_FLEET AS
SELECT
    TS_UTC AS `Timestamp`,
    V_LAT AS `Latitude`,
    V_LON AS `Longitude`,
    CAST(IOT_TEMP_VAL_C AS DECIMAL(10, 2)) AS `Current_Temperature_C`,
    CGO_COND_CD AS `Cargo_Condition_Code`,
    RISK_CLS_TXT AS `Risk_Classification`,
    DELAY_PROB_DEC AS `Delay_Probability`,
    PRT_CNG_LVL AS `Port_Congestion_Level`,
    RT_RSK_IDX AS `Route_Risk_Index`
FROM logistics.TBL_SC_FLEET_HIST_RAW;

-- Grant the AI user access only to the view
GRANT SELECT
ON FDE_VIEWS.VW_ACTIVE_FLEET
TO 'usr_fde_ro'@'%';

-- Verify the AI account's grants
SHOW GRANTS FOR 'usr_fde_ro'@'%';

