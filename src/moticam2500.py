import usb.core
import usb
import usb.util


VID = 0x0634
PID = 0x1003


camara = usb.core.find(idVendor=VID, idProduct=PID)

if camara is None:
    print("Moticam 2500 no encontrada.")
    exit()


print("Cámara encontrada.")
print(f"VID: {camara.idVendor:04X}")
print(f"PID: {camara.idProduct:04X}")

print("\nInterfaces USB:")

for cfg in camara:

    print(f"\nConfiguración {cfg.bConfigurationValue}")

    for interfaz in cfg:

        print(f"Interface {interfaz.bInterfaceNumber}")

        for endpoint in interfaz:

            direccion = (
                "IN"
                if usb.util.endpoint_direction(
                    endpoint.bEndpointAddress
                ) == usb.util.ENDPOINT_IN
                else "OUT"
            )

            tipo = usb.util.endpoint_type(
                endpoint.bmAttributes
            )

            print(
                f"    Endpoint: 0x{endpoint.bEndpointAddress:02X}, "
                f"{direccion}, "
                f"max packet: {endpoint.wMaxPacketSize}, "
                f"type: {tipo}"
            )
            
