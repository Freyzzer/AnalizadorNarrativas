-- Limpiar guest_id de filas que ya tienen usuario_id (causaba leak de datos entre sesiones)
-- Ejecutar una sola vez contra Neon.

UPDATE personaje_historial SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE inconsistencias     SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE hechos_continuidad  SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE analisis            SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE chats               SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE capitulos           SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE obras               SET guest_id = NULL WHERE usuario_id IS NOT NULL;
UPDATE personajes          SET guest_id = NULL WHERE usuario_id IS NOT NULL;
