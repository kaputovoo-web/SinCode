cmake_minimum_required(VERSION 3.24)
project(MAKE LANGUAGES C ASM)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(MCU_FLAGS    -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard)
set(MCU_DEFINES  STM32F40_41xxx USE_STDPERIPH_DRIVER)
set(MCU_STARTUP  ${CMAKE_CURRENT_SOURCE_DIR}/Driver/startup/startup_stm32f40_41xxx.s)
set(MCU_LDSCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/linker/STM32F407VET6.ld)

add_library(cmsis INTERFACE)
target_include_directories(cmsis SYSTEM INTERFACE
    Driver/CMSIS/Include
    Driver/CMSIS/Device/ST/STM32F4xx/Include
)
target_compile_definitions(cmsis INTERFACE ${MCU_DEFINES})
target_compile_options(cmsis INTERFACE ${MCU_FLAGS} -ffreestanding)
target_link_options(cmsis INTERFACE ${MCU_FLAGS})

# std library
set(STDP_DIR Driver/STM32F4xx_StdPeriph_Driver)
add_library(stdperiph STATIC
    ${STDP_DIR}/src/misc.c
    ${STDP_DIR}/src/stm32f4xx_gpio.c
    ${STDP_DIR}/src/stm32f4xx_rcc.c
    ${STDP_DIR}/src/stm32f4xx_syscfg.c
    ${STDP_DIR}/src/stm32f4xx_flash.c
    ${STDP_DIR}/src/stm32f4xx_usart.c
)
target_include_directories(stdperiph SYSTEM PUBLIC ${STDP_DIR}/inc)
target_include_directories(stdperiph PUBLIC Core/inc)   # stm32f4xx_conf.h 在这里
target_link_libraries(stdperiph PUBLIC cmsis)

# 固件 bin hex
file(GLOB_RECURSE APP_SRC CONFIGURE_DEPENDS app/*.c)

add_executable(MAKE
    ${APP_SRC}
    Core/src/system_stm32f4xx.c
    ${MCU_STARTUP}
)
target_include_directories(MAKE PRIVATE app/inc)
target_link_libraries(MAKE PRIVATE stdperiph gcc)
target_compile_options(MAKE PRIVATE -Wall -Wextra -g -Og -ffunction-sections -fdata-sections)
target_link_options(MAKE PRIVATE
    -T${MCU_LDSCRIPT}
    -nostdlib -nostartfiles
    -Wl,--gc-sections
    -Wl,-Map=$<TARGET_FILE_DIR:MAKE>/MAKE.map
    -Wl,--print-memory-usage
)
set_target_properties(MAKE PROPERTIES LINK_DEPENDS ${MCU_LDSCRIPT})

add_custom_command(TARGET MAKE POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:MAKE> $<TARGET_FILE_DIR:MAKE>/MAKE.bin
    COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:MAKE> $<TARGET_FILE_DIR:MAKE>/MAKE.hex
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:MAKE>
    VERBATIM
)
