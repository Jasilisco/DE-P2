CREATE TABLE IF NOT EXISTS dim_driver (
  driver_id INT AUTO_INCREMENT PRIMARY KEY,
  driver_nk INT NOT NULL,                       -- drivers.driverId
  driver_ref VARCHAR(64) NOT NULL,
  code VARCHAR(16),
  forename VARCHAR(100),
  surname VARCHAR(100),
  nationality VARCHAR(100),
  url VARCHAR(255),
  number INT,
  UNIQUE KEY uq_driver_nk (driver_nk),
  UNIQUE KEY uq_driverRef (driver_ref)
) engine=InnoDB;

CREATE TABLE IF NOT EXISTS dim_circuit (
  circuit_id INT AUTO_INCREMENT PRIMARY KEY,
  circuit_nk INT NOT NULL,          -- circuits.circuit_id
  circuit_ref VARCHAR(64) NOT NULL,
  name VARCHAR(200),
  location VARCHAR(200),
  country VARCHAR(100),
  altitude INT,
  latitude DECIMAL(9,6),
  longitude DECIMAL(9,6),
  url VARCHAR(255),
  UNIQUE KEY uq_circuit_nk (circuit_nk),
  UNIQUE KEY uq_circuitRef (circuit_ref)
) engine=InnoDB;

CREATE TABLE IF NOT EXISTS dim_date (
  date_id INT AUTO_INCREMENT PRIMARY KEY,
  date DATE NOT NULL,
  year SMALLINT,
  month TINYINT,
  day TINYINT,
  UNIQUE KEY uq_date (date)
) engine=InnoDB;

CREATE TABLE IF NOT EXISTS dim_race (
  race_id INT AUTO_INCREMENT PRIMARY KEY,
  race_nk INT NOT NULL,         -- races.raceId
  name VARCHAR(200),
  round INT,
  year SMALLINT,
  url VARCHAR(255),
  UNIQUE KEY uq_race_nk (race_nk)
) engine=InnoDB;

CREATE TABLE IF NOT EXISTS fact_pit_stops (
  pit_stop_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  race_id INT,
  driver_id INT,
  circuit_id INT,
  date_id INT,

  stop INT,
  lap INT,
  duration_ms INT,

  UNIQUE KEY uq_fact_pit (race_id, driver_id, stop, lap),

  KEY ix_fp_race (race_id),
  KEY ix_fp_driver (driver_id),
  KEY ix_fp_circuit (circuit_id),
  KEY ix_fp_date (date_id),

  CONSTRAINT fk_fp_driver   FOREIGN KEY (driver_id)  REFERENCES dim_driver(driver_id),
  CONSTRAINT fk_fp_circuit  FOREIGN KEY (circuit_id) REFERENCES dim_circuit(circuit_id),
  CONSTRAINT fk_fp_date     FOREIGN KEY (date_id)    REFERENCES dim_date(date_id),
  CONSTRAINT fk_fp_race     FOREIGN KEY (race_id)    REFERENCES dim_race(race_id)
) engine=InnoDB;
