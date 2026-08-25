#include "usart.h"
#include <stdint.h>
#include "led.h"

static void delay_ms(uint32_t ms);
int main(void)
{
    SystemInit();
    uart_init();
    led_init();

    while(1){
        GPIO_ToggleBits(GPIOB, GPIO_Pin_4);
        delay_ms(1000);
        uart_send_str("Hello World\r\n");
    }
}


static void delay_ms(uint32_t ms)
{
    uint32_t start = uart_get_ms();
    while ((uint32_t)(uart_get_ms() - start) < ms) {
        __WFI();   
    }
}
