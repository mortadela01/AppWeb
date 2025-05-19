CREATE DATABASE IF NOT EXISTS vr_mausoleum;
USE vr_mausoleum;

-- Table: USER
CREATE TABLE TBL_USER (
    id_user BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    password VARCHAR(250)
);

-- Table: DECEASED
CREATE TABLE TBL_DECEASED (
    id_deceased BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    date_birth DATETIME,
    date_death DATETIME,
    description VARCHAR(100),
    burial_place VARCHAR(100),
    visualization_state BOOLEAN,
    visualization_code VARCHAR(100)
);

-- Table: VIDEO
CREATE TABLE TBL_VIDEO (
    id_video BIGINT AUTO_INCREMENT PRIMARY KEY,
    video_link VARCHAR(1000),
    event_title VARCHAR(100),
    description VARCHAR(100)
);

-- Table: VIDEO_METADATA
CREATE TABLE TBL_VIDEO_METADATA (
    id_metadata BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_created DATETIME,
    coordinates VARCHAR(100)
);

-- Table: DECEASED_VIDEO
CREATE TABLE TBL_DECEASED_VIDEO (
	id_deceased_video BIGINT AUTO_INCREMENT PRIMARY KEY,
	id_video BIGINT,
    id_deceased BIGINT,
    id_metadata BIGINT,
    video_link VARCHAR(1000),
    UNIQUE KEY (id_deceased, id_metadata),
    FOREIGN KEY (id_deceased) REFERENCES TBL_DECEASED(id_deceased),
    FOREIGN KEY (id_video) REFERENCES TBL_VIDEO(id_video),
    FOREIGN KEY (id_metadata) REFERENCES TBL_VIDEO_METADATA(id_metadata)
);

-- Table: IMAGE
CREATE TABLE TBL_IMAGE (
    id_image BIGINT AUTO_INCREMENT PRIMARY KEY,
    image_link VARCHAR(1000),
    event_title VARCHAR(100),
    description VARCHAR(100)
);

-- Table: IMAGE_METADATA
CREATE TABLE TBL_IMAGE_METADATA (
    id_metadata BIGINT AUTO_INCREMENT PRIMARY KEY,
    date_created DATETIME,
    coordinates VARCHAR(100)
);

-- Table: DECEASED_IMAGE
CREATE TABLE TBL_DECEASED_IMAGE (
	id_deceased_image BIGINT AUTO_INCREMENT PRIMARY KEY,
	id_image BIGINT,
    id_deceased BIGINT,
    id_metadata BIGINT,
    image_link VARCHAR(1000),
    UNIQUE KEY (id_image, id_deceased, id_metadata),
    FOREIGN KEY (id_deceased) REFERENCES TBL_DECEASED(id_deceased),
    FOREIGN KEY (id_image) REFERENCES TBL_IMAGE(id_image),
    FOREIGN KEY (id_metadata) REFERENCES TBL_IMAGE_METADATA(id_metadata)
);

-- Table: RELATIONSHIP_TYPE
CREATE TABLE TBL_RELATIONSHIP_TYPE (
    relationship VARCHAR(100) PRIMARY KEY
);

-- Table: RELATION
CREATE TABLE TBL_RELATION (
	id_relation BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_deceased BIGINT,
    id_parent BIGINT,
    relationship VARCHAR(100),
    UNIQUE KEY (id_deceased, id_parent),
    FOREIGN KEY (id_deceased) REFERENCES TBL_DECEASED(id_deceased),
    FOREIGN KEY (id_parent) REFERENCES TBL_DECEASED(id_deceased),
    FOREIGN KEY (relationship) REFERENCES TBL_RELATIONSHIP_TYPE(relationship)
);

-- Table: USER_DECEASED
CREATE TABLE TBL_USER_DECEASED (
	id_user_deceased BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_user BIGINT,
    id_deceased BIGINT,
    date_relation DATETIME,
    has_permission BOOLEAN,
    UNIQUE KEY (id_user, id_deceased),
    FOREIGN KEY (id_user) REFERENCES TBL_USER(id_user),
    FOREIGN KEY (id_deceased) REFERENCES TBL_DECEASED(id_deceased)
);

-- Table: REQUEST
CREATE TABLE TBL_REQUEST (
    id_request BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_issuer BIGINT,
    id_receiver BIGINT,
    id_deceased BIGINT,
    creation_date DATE,
    request_type VARCHAR(50),
    request_status VARCHAR(50),
    FOREIGN KEY (id_issuer) REFERENCES TBL_USER(id_user),
    FOREIGN KEY (id_receiver) REFERENCES TBL_USER(id_user),
    FOREIGN KEY (id_deceased) REFERENCES TBL_DECEASED(id_deceased)
);

-- Table: NOTIFICATION
CREATE TABLE TBL_NOTIFICATION (
    id_notification BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_sender BIGINT,
    id_receiver BIGINT,
    message VARCHAR(1000),
    is_read BOOLEAN DEFAULT FALSE,
    creation_date DATETIME,
    FOREIGN KEY (id_sender) REFERENCES TBL_USER(id_user),
    FOREIGN KEY (id_receiver) REFERENCES TBL_USER(id_user)
);

-- Table: QR
CREATE TABLE TBL_QR (
    id_qr BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_user BIGINT,
    qr_code BIGINT NOT NULL UNIQUE,
    visualization_status VARCHAR(50),
    generation_date DATETIME,
    FOREIGN KEY (id_user) REFERENCES TBL_USER(id_user)
);


ALTER TABLE TBL_USER ADD UNIQUE (email);

INSERT INTO TBL_RELATIONSHIP_TYPE (relationship) VALUES
('parent'),
('child'),
('sibling'),
('spouse');