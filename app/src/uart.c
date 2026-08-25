#include "usart.h"
#include "stm32f4xx.h"

#define UART_RX_BUF_SIZE 256u

static volatile uint8_t  g_rxbuf[UART_RX_BUF_SIZE];
static volatile uint16_t g_rx_head = 0;
static volatile uint16_t g_rx_tail = 0;
static volatile uint32_t g_ms = 0;

void SysTick_Handler(void)   
{
    g_ms++;
}

void USART6_IRQHandler(void) 
{
    if (USART6->SR & USART_SR_RXNE) {
        uint8_t b = (uint8_t)(USART6->DR & 0xFF);
        uint16_t next = (uint16_t)((g_rx_head + 1) % UART_RX_BUF_SIZE);
        if (next != g_rx_tail) {
            g_rxbuf[g_rx_head] = b;
            g_rx_head = next;
        }
    }
}

void uart_init(void)
{
    GPIO_InitTypeDef  gpio;
    USART_InitTypeDef usart;
    NVIC_InitTypeDef  nvic;

    RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOC, ENABLE);   
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART6, ENABLE);  

    GPIO_PinAFConfig(GPIOC, GPIO_PinSource6, GPIO_AF_USART6);  /* PC6=TX */
    GPIO_PinAFConfig(GPIOC, GPIO_PinSource7, GPIO_AF_USART6);  /* PC7=RX */

    gpio.GPIO_Pin   = GPIO_Pin_6 | GPIO_Pin_7;
    gpio.GPIO_Mode  = GPIO_Mode_AF;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    gpio.GPIO_OType = GPIO_OType_PP;
    gpio.GPIO_PuPd  = GPIO_PuPd_UP;
    GPIO_Init(GPIOC, &gpio);

    usart.USART_BaudRate            = 115200;
    usart.USART_WordLength          = USART_WordLength_8b;
    usart.USART_StopBits            = USART_StopBits_1;
    usart.USART_Parity              = USART_Parity_No;
    usart.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    usart.USART_Mode                = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART6, &usart);

    USART_ITConfig(USART6, USART_IT_RXNE, ENABLE);
    USART_Cmd(USART6, ENABLE);

    nvic.NVIC_IRQChannel                   = USART6_IRQn;   /* 71 */
    nvic.NVIC_IRQChannelPreemptionPriority = 0;
    nvic.NVIC_IRQChannelSubPriority        = 0;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    SysTick_Config(SystemCoreClock / 1000);
}

int uart_rx_get(uint8_t *b)
{
    if (g_rx_tail != g_rx_head) {
        *b = g_rxbuf[g_rx_tail];
        g_rx_tail = (uint16_t)((g_rx_tail + 1) % UART_RX_BUF_SIZE);
        return 1;
    }
    return 0;
}

uint32_t uart_get_ms(void)
{
    return g_ms;
}

/* ================= 调试输出（USART6 TX / PC6） ================= */
void uart_send_char(uint8_t c)
{
    while (!(USART6->SR & USART_SR_TXE)) {}
    USART6->DR = c;
}

void uart_send_str(const char *s)
{
    while (*s) uart_send_char((uint8_t)*s++);
}

void uart_send_hex(uint32_t v, uint8_t digits)
{
    int i;
    for (i = (int)digits - 1; i >= 0; i--) {
        uint8_t nib = (uint8_t)((v >> (4 * i)) & 0x0F);
        uart_send_char(nib < 10 ? (uint8_t)('0' + nib) : (uint8_t)('A' + nib - 10));
    }
}
