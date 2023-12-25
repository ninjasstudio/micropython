if 1:    
#try:
    import machine, time, esp
    
    from stepper import Stepper


    pin = 26 # machine.Pin(26)  # 
    dir_pin = machine.Pin(23, machine.Pin.OUT, value=1)
    
    counter = machine.Counter(0, pin, direction=dir_pin)
    match1 = 100
    match2 = 200

    stepper = Stepper('', pin, dir_pin)
    print(stepper)

    def irq_handler1(obj):
        obj_value = obj.value()
        print()
        print("1 obj.value()=", obj_value, 'obj.status()=', obj.status())
        #counter.irq(handler=irq_handler1, trigger=machine.Counter.IRQ_MATCH1, value=obj_value+2500)
        print("irq_handler1: obj=", obj)
        print()
        
    def irq_handler2(obj):
        obj_value = obj.value()
        print()
        print("2 obj.value()=", obj_value, 'obj.status()=', obj.status())
        #counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=obj_value+2500)
        print("irq_handler2: obj=", obj)
        print()

    def irq_handler0(obj):
        obj_value = obj.value()
        print()
        print("0 obj.value()=", obj_value, 'obj.status()=', obj.status())
        #counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=obj_value+2500)
        print("irq_handler0: obj=", obj)
        print()

    counter.value(0)
    counter.irq(handler=irq_handler1, trigger=machine.Counter.IRQ_MATCH1, value=match1)  
#     counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=match2)
#     counter.irq(handler=irq_handler0, trigger=machine.Counter.IRQ_ZERO)
    counter.value(0)
    print(counter)
    print(counter.value())
    
    stepper.go(250)
    print(counter.value())
    
    time.sleep(2)
    #1/0

    stepper.go(0)
    print(counter.value())

    time.sleep(2)
    #1/0

    counter.irq(handler=irq_handler1, trigger=machine.Counter.IRQ_MATCH1, value=-match1)  
#     counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=-match2)
    print(counter)
    print(counter.value())
    
    stepper.go(250)
    print(counter.value())
    time.sleep(2)

    stepper.go(-250)
    print(counter.value())

    time.sleep(2)
    1/0

    stepper.go(0)
    print(counter.value())

    time.sleep(2)
    1/0
    
    

    while 1:
        print("counter.value()=", counter.value(), 'match1=', match1, 'match2=', match2)
        if (counter.value() >= match2) and (match2 > 0) or (counter.value() <= match2) and (match2 < 0):
            #match1 += 2000
            match2 = - match2
            #counter.pause()
            counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=match2)
            #counter.resume()
            dir_pin.value(not dir_pin.value())
            print('set irq2:', dir_pin.value(), counter)

            
#         if counter.value() > match2:
#             match2 += 5000
#             counter.irq(handler=irq_handler2, trigger=machine.Counter.IRQ_MATCH2, value=match2)
#             print('set irq2:', counter)

        time.sleep(1.0)

# except Exception as e:
#     try:
#         counter.deinit()
#         print('counter.deinit()')
#     except:
#         pass
# 