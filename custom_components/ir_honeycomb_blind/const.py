"""Constants for IR Honeycomb Blind integration."""

DOMAIN = "ir_honeycomb_blind"

# Configuration keys
CONF_BLIND_NAME = "blind_name"
CONF_REMOTE_ENTITY = "remote_entity"
CONF_IR_CODE_T_UP = "ir_code_t_up"
CONF_IR_CODE_T_DN = "ir_code_t_dn"
CONF_IR_CODE_B_UP = "ir_code_b_up"
CONF_IR_CODE_B_DN = "ir_code_b_dn"
CONF_IR_CODE_STOP = "ir_code_stop"
CONF_T_OPEN = "t_open"
CONF_T_CLOSE = "t_close"
CONF_IR_REPEAT = "ir_repeat"
CONF_IR_REPEAT_DELAY = "ir_repeat_delay"
CONF_DEBOUNCE_DELAY = "debounce_delay"

# Default values
DEFAULT_T_OPEN = 30.0
DEFAULT_T_CLOSE = 30.0
DEFAULT_IR_REPEAT = 3
DEFAULT_IR_REPEAT_DELAY = 0.3
DEFAULT_DEBOUNCE_DELAY = 1.0

# Position limits
POS_MIN = 0
POS_MAX = 100

# State keys for persistence
ATTR_POS = "pos"
ATTR_RATIO = "ratio"
ATTR_TOP_POS = "top_pos"

# Entity suffixes
ENTITY_SUFFIX_POSITION = "position"
ENTITY_SUFFIX_RATIO = "ratio"
