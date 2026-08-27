# # is the normal comment marker.
a = ON
b = OFF

? a && b
? a || b
? a ^^ b
? ~b
? ¬b

# Compatibility mode gives && its classic xBase comment meaning.
SET AMPERSAND_COMMENT ON
value = 42 && this is now a comment
? value
SET AMPERSAND_COMMENT OFF
