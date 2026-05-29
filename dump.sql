


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE TYPE "public"."vehicle_condition_status" AS ENUM (
    'Good',
    'Very Good',
    'Excellent',
    'Under Maintenance'
);


ALTER TYPE "public"."vehicle_condition_status" OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."drivers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "full_name" "text" NOT NULL,
    "license_number" "text" NOT NULL,
    "phone_number" "text",
    "work_status" "text" DEFAULT 'Available'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    CONSTRAINT "drivers_work_status_check" CHECK (("work_status" = ANY (ARRAY['Available'::"text", 'On Trip'::"text", 'On Leave'::"text", 'Suspended'::"text"])))
);


ALTER TABLE "public"."drivers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."fleet_fuel_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "vehicle_id" "uuid",
    "fuel_date" "date" DEFAULT CURRENT_DATE,
    "liters_fueled" numeric(10,2) NOT NULL,
    "cost_etb" numeric(10,2) NOT NULL,
    "odometer_reading" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."fleet_fuel_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."fleet_monthly_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "vehicle_id" "uuid",
    "log_month_year" "date" NOT NULL,
    "starting_km" numeric(12,2) DEFAULT 0.0,
    "ending_km" numeric(12,2) DEFAULT 0.0,
    "km_driven" numeric(12,2) DEFAULT 0.0,
    "fuel_consumption_liters" numeric(10,4) DEFAULT 0.0000,
    "fuel_cost_etb" numeric(12,2) DEFAULT 0.00,
    "maintenance_cost_etb" numeric(12,2) DEFAULT 0.00,
    "fuel_efficiency" numeric(10,4),
    "working_days" integer DEFAULT 26,
    "days_available" integer DEFAULT 26,
    "days_under_maintenance" integer DEFAULT 0,
    "idle_days" integer DEFAULT 0,
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."fleet_monthly_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."fleet_vehicles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "plate_number" character varying(50) NOT NULL,
    "vehicle_model" character varying(100) NOT NULL,
    "condition_status" "public"."vehicle_condition_status" DEFAULT 'Good'::"public"."vehicle_condition_status",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "project_assignment" character varying DEFAULT 'General Operations'::character varying,
    "current_odometer" bigint DEFAULT 0,
    "is_in_workshop" boolean DEFAULT false,
    "current_driver_id" "uuid"
);


ALTER TABLE "public"."fleet_vehicles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."telematics_logs" (
    "id" bigint NOT NULL,
    "vehicle_id" "uuid" NOT NULL,
    "latitude" numeric(9,6) NOT NULL,
    "longitude" numeric(9,6) NOT NULL,
    "current_speed_kmh" numeric(5,2) DEFAULT 0.0,
    "fuel_level_percent" numeric(5,2),
    "logged_at" timestamp with time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL
);


ALTER TABLE "public"."telematics_logs" OWNER TO "postgres";


ALTER TABLE "public"."telematics_logs" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "public"."telematics_logs_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



ALTER TABLE ONLY "public"."drivers"
    ADD CONSTRAINT "drivers_license_number_key" UNIQUE ("license_number");



ALTER TABLE ONLY "public"."drivers"
    ADD CONSTRAINT "drivers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fleet_fuel_logs"
    ADD CONSTRAINT "fleet_fuel_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fleet_monthly_logs"
    ADD CONSTRAINT "fleet_monthly_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fleet_vehicles"
    ADD CONSTRAINT "fleet_vehicles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."fleet_vehicles"
    ADD CONSTRAINT "fleet_vehicles_plate_number_key" UNIQUE ("plate_number");



ALTER TABLE ONLY "public"."telematics_logs"
    ADD CONSTRAINT "telematics_logs_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_fleet_logs_date" ON "public"."fleet_monthly_logs" USING "btree" ("log_month_year");



CREATE INDEX "idx_fleet_logs_vehicle" ON "public"."fleet_monthly_logs" USING "btree" ("vehicle_id");



CREATE INDEX "idx_logs_vehicle_month" ON "public"."fleet_monthly_logs" USING "btree" ("vehicle_id", "log_month_year");



CREATE INDEX "idx_telematics_vehicle_time" ON "public"."telematics_logs" USING "btree" ("vehicle_id", "logged_at" DESC);



CREATE INDEX "idx_vehicles_plate" ON "public"."fleet_vehicles" USING "btree" ("plate_number");



ALTER TABLE ONLY "public"."fleet_fuel_logs"
    ADD CONSTRAINT "fleet_fuel_logs_vehicle_id_fkey" FOREIGN KEY ("vehicle_id") REFERENCES "public"."fleet_vehicles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."fleet_monthly_logs"
    ADD CONSTRAINT "fleet_monthly_logs_vehicle_id_fkey" FOREIGN KEY ("vehicle_id") REFERENCES "public"."fleet_vehicles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."fleet_vehicles"
    ADD CONSTRAINT "fleet_vehicles_current_driver_id_fkey" FOREIGN KEY ("current_driver_id") REFERENCES "public"."drivers"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."telematics_logs"
    ADD CONSTRAINT "telematics_logs_vehicle_id_fkey" FOREIGN KEY ("vehicle_id") REFERENCES "public"."fleet_vehicles"("id") ON DELETE CASCADE;





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";





GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";














































































































































































GRANT ALL ON TABLE "public"."drivers" TO "anon";
GRANT ALL ON TABLE "public"."drivers" TO "authenticated";
GRANT ALL ON TABLE "public"."drivers" TO "service_role";



GRANT ALL ON TABLE "public"."fleet_fuel_logs" TO "anon";
GRANT ALL ON TABLE "public"."fleet_fuel_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."fleet_fuel_logs" TO "service_role";



GRANT ALL ON TABLE "public"."fleet_monthly_logs" TO "anon";
GRANT ALL ON TABLE "public"."fleet_monthly_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."fleet_monthly_logs" TO "service_role";



GRANT ALL ON TABLE "public"."fleet_vehicles" TO "anon";
GRANT ALL ON TABLE "public"."fleet_vehicles" TO "authenticated";
GRANT ALL ON TABLE "public"."fleet_vehicles" TO "service_role";



GRANT ALL ON TABLE "public"."telematics_logs" TO "anon";
GRANT ALL ON TABLE "public"."telematics_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."telematics_logs" TO "service_role";



GRANT ALL ON SEQUENCE "public"."telematics_logs_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."telematics_logs_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."telematics_logs_id_seq" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































