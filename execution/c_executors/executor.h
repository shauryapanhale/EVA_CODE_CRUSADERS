#define EXECUTOR_H

int mouse_move(int x, int y);
int mouse_click(int button);
int mouse_scroll(int amount);
int keyboard_press_key(int vk_code);
int keyboard_type_string(const char* text);