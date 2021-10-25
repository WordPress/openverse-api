--
-- PostgreSQL database dump
--

-- Dumped from database version 13.2
-- Dumped by pg_dump version 13.3 (Debian 13.3-1.pgdg100+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audio_view; Type: TABLE; Schema: public; Owner: deploy
--

CREATE TABLE public.audio_view (
    id integer NOT NULL,
    created_on timestamp with time zone NOT NULL,
    updated_on timestamp with time zone NOT NULL,
    identifier uuid NOT NULL,
    foreign_identifier character varying(1000),
    title character varying(2000),
    foreign_landing_url character varying(1000),
    creator character varying(2000),
    creator_url character varying(2000),
    url character varying(1000),
    filesize integer,
    watermarked boolean,
    license character varying(50) NOT NULL,
    license_version character varying(25),
    provider character varying(80),
    source character varying(80),
    last_synced_with_source timestamp with time zone,
    removed_from_source boolean NOT NULL,
    view_count integer,
    tags jsonb,
    tags_list character varying(255)[],
    meta_data jsonb,
    audio_set_position integer,
    genres character varying(80)[],
    category character varying(80),
    duration integer,
    bit_rate integer,
    sample_rate integer,
    alt_files jsonb,
    thumbnail character varying(1000),
    filetype character varying(80),
    audio_set_foreign_identifier character varying(1000),
    standardized_popularity double precision,
    ingestion_type character varying(1000),
    audio_set jsonb
);


ALTER TABLE public.audio_view OWNER TO deploy;

--
-- Name: audio_id_seq; Type: SEQUENCE; Schema: public; Owner: deploy
--

CREATE SEQUENCE public.audio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.audio_id_seq OWNER TO deploy;

--
-- Name: audio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: deploy
--

ALTER SEQUENCE public.audio_id_seq OWNED BY public.audio_view.id;


--
-- Name: audio_view id; Type: DEFAULT; Schema: public; Owner: deploy
--

ALTER TABLE ONLY public.audio_view ALTER COLUMN id SET DEFAULT nextval('public.audio_id_seq'::regclass);


--
-- Name: audio_view audio_identifier_key; Type: CONSTRAINT; Schema: public; Owner: deploy
--

ALTER TABLE ONLY public.audio_view
    ADD CONSTRAINT audio_identifier_key UNIQUE (identifier);


--
-- Name: audio_view audio_pkey; Type: CONSTRAINT; Schema: public; Owner: deploy
--

ALTER TABLE ONLY public.audio_view
    ADD CONSTRAINT audio_pkey PRIMARY KEY (id);


--
-- Name: audio_view audio_url_key; Type: CONSTRAINT; Schema: public; Owner: deploy
--

ALTER TABLE ONLY public.audio_view
    ADD CONSTRAINT audio_url_key UNIQUE (url);


--
-- Name: audio_view unique_provider_audio; Type: CONSTRAINT; Schema: public; Owner: deploy
--

ALTER TABLE ONLY public.audio_view
    ADD CONSTRAINT unique_provider_audio UNIQUE (foreign_identifier, provider);


--
-- Name: audio_category_ceb7d386; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_category_ceb7d386 ON public.audio_view USING btree (category);


--
-- Name: audio_category_ceb7d386_like; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_category_ceb7d386_like ON public.audio_view USING btree (category varchar_pattern_ops);


--
-- Name: audio_foreign_identifier_617f66ad; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_foreign_identifier_617f66ad ON public.audio_view USING btree (foreign_identifier);


--
-- Name: audio_foreign_identifier_617f66ad_like; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_foreign_identifier_617f66ad_like ON public.audio_view USING btree (foreign_identifier varchar_pattern_ops);


--
-- Name: audio_genres_e34cc474; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_genres_e34cc474 ON public.audio_view USING btree (genres);


--
-- Name: audio_last_synced_with_source_94c4a383; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_last_synced_with_source_94c4a383 ON public.audio_view USING btree (last_synced_with_source);


--
-- Name: audio_provider_8fe1eb54; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_provider_8fe1eb54 ON public.audio_view USING btree (provider);


--
-- Name: audio_provider_8fe1eb54_like; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_provider_8fe1eb54_like ON public.audio_view USING btree (provider varchar_pattern_ops);


--
-- Name: audio_source_e9ccc813; Type: INDEX; Schema: public; Owner: deploy
--

CREATE INDEX audio_source_e9ccc813 ON public.audio_view USING btree (source);


--
-- PostgreSQL database dump complete
--
