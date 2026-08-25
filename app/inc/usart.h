#ifndef __USART_H
#define __USART_H

#include "stm32f4xx.h"
#include "stm32f4xx_gpio.h"
#include "stm32f4xx_rcc.h"
#include "stm32f4xx_usart.h"
#include "misc.h"

void     uart_init(void);
int      uart_rx_get(uint8_t *b);
uint32_t uart_get_ms(void);
void     uart_send_char(uint8_t c);
void     uart_send_str(const char *s);
void     uart_send_hex(uint32_t v, uint8_t digits);



#endif
