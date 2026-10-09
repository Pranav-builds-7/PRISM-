CREATE TABLE IF NOT EXISTS FDE_VIEWS.AgentAuditLog (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    SessionID VARCHAR(50),
    NodeExecuted VARCHAR(50),
    ToolName VARCHAR(100),
    Content LONGTEXT
);

-- The read-only AI account may append audit events and read the audit trail
-- (and nothing else: no access to the raw logistics table).
GRANT INSERT, SELECT
ON FDE_VIEWS.AgentAuditLog
TO 'usr_fde_ro'@'%';

