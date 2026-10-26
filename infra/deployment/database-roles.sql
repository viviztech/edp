-- REVIEW AND RUN ONLY by the database owner after provisioning three separate
-- NOINHERIT LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS identities.
-- psql variables: database, migration_role, api_role, worker_role. Passwords are
-- supplied by the secret manager, never by this file or command-line arguments.
-- Run migrations as migration_role, then rerun this grant policy after migration.
\set ON_ERROR_STOP on
BEGIN;
REVOKE ALL ON DATABASE :"database" FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database" TO :"migration_role", :"api_role", :"worker_role";
ALTER SCHEMA public OWNER TO :"migration_role";
REVOKE ALL ON SCHEMA public FROM :"api_role", :"worker_role";
GRANT USAGE ON SCHEMA public TO :"api_role", :"worker_role";
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :"api_role", :"worker_role";
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM :"api_role", :"worker_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"api_role";
REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM :"api_role";
REVOKE UPDATE, DELETE ON audit_logs FROM :"api_role";
-- Worker reads are explicit; API permission changes must not silently grant a
-- background process access to every future domain table.
GRANT SELECT ON users, people, organizations, roles, permissions,
  role_permissions, user_roles, participants, enrollments, programs, cohorts,
  application_cycles, applications, crm_leads, crm_lead_activities,
  meta_integrations, meta_form_mappings, notification_preferences,
  helpdesk_tickets, helpdesk_preferences, file_policies, application_documents,
  application_document_evidence, cms_asset_files, cms_assets,
  assignment_submissions, certificates, lesson_materials, report_exports,
  participant_notice_preferences, verification_tokens
  TO :"worker_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON auth_deliveries, meta_webhook_events,
  notification_intents, domain_outbox, participant_notices,
  crm_export_jobs, file_objects TO :"worker_role";
GRANT UPDATE ON crm_leads, crm_lead_activities TO :"worker_role";
GRANT INSERT ON crm_leads, audit_logs TO :"worker_role";
GRANT SELECT ON audit_logs TO :"worker_role";
-- PostgreSQL row locking needs UPDATE on at least one column even when no value
-- is changed. Only the primary identifier is granted for authorization fencing;
-- related foreign keys and domain triggers still apply. No role/permission fields.
GRANT UPDATE (id) ON users, user_roles, verification_tokens, participants,
  enrollments, applications, notification_preferences,
  participant_notice_preferences TO :"worker_role";
GRANT UPDATE (role_id) ON role_permissions TO :"worker_role";
-- No TRUNCATE, REFERENCES, TRIGGER, schema CREATE or membership in the owner.
-- No defaults: new tables are unavailable until this reviewed policy is updated.
COMMIT;
