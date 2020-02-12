
DROP TABLE IF EXISTS Asm_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Ben_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Guj_4_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Hin_4_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Kan_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Mal_4_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Mar_4_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Odi_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Pun_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Tam_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Tel_5_Grk_UGNT4_Alignment_History ;
DROP TABLE IF EXISTS Urd_5_Grk_UGNT4_Alignment_History ;

CREATE TABLE Asm_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Ben_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Guj_4_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Hin_4_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Kan_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Mal_4_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Mar_4_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Odi_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Pun_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Tam_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Tel_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;
CREATE TABLE Urd_5_Grk_UGNT4_Alignment_History LIKE Asm_5_Grk_UGNT4_Alignment;

DELIMITER //
CREATE TRIGGER Asm_history_logger AFTER INSERT ON Asm_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Asm_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 


DELIMITER //
CREATE TRIGGER Ben_history_logger AFTER INSERT ON Ben_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Ben_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Guj_history_logger AFTER INSERT ON Guj_4_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Guj_4_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Hin_history_logger AFTER INSERT ON Hin_4_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Hin_4_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Kan_history_logger AFTER INSERT ON Kan_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Kan_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Mar_history_logger AFTER INSERT ON Mar_4_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Mar_4_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Mal_history_logger AFTER INSERT ON Mal_4_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Mal_4_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Odi_history_logger AFTER INSERT ON Odi_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Odi_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Pun_history_logger AFTER INSERT ON Pun_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Pun_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Tam_history_logger AFTER INSERT ON Tam_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Tam_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Tel_history_logger AFTER INSERT ON Tel_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Tel_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 

DELIMITER //
CREATE TRIGGER Urd_history_logger AFTER INSERT ON Urd_5_Grk_UGNT4_Alignment FOR EACH ROW
BEGIN 
INSERT INTO Urd_5_Grk_UGNT4_Alignment_History(LidSrc, LidTrg, PositionSrc, PositionTrg, WordSrc,Strongs, UserId,Type, Stage,UpdatedOn)  
VALUES(NEW.LidSrc, NEW.LidTrg, NEW.PositionSrc, NEW.PositionTrg, NEW.WordSrc,NEW.Strongs, NEW.UserId,NEW.Type, NEW.Stage,NEW.UpdatedOn);
END // 