from networktables import NetworkTables
import cv2
import imutils
import zmq
import socket
from decouple import config
from misc.functions import functions


hsv_lower = (int(config("H_LOWER")), int(config("S_LOWER")), int(config("V_LOWER")))
hsv_upper = (int(config("H_UPPER")), int(config("S_UPPER")), int(config("V_UPPER")))

kpw = int(config("KNOWN_PIXEL_WIDTH"))
kd = int(config("KNOWN_DISTANCE"))
kw = int(config("KNOWN_WIDTH"))

NetworkTables.initialize(server="roborio-7672-frc.local")
table = NetworkTables.getTable("vision")

camera = functions.os_action()

cascade_classifier = cv2.CascadeClassifier("cascade.xml")

hostname = socket.gethostname()
host_ip = socket.gethostbyname(hostname)
context = zmq.Context()
footage_socket = context.socket(zmq.PUB)
footage_socket.connect(f"tcp://{host_ip}:5555")

flask_popen = functions.run_flask()


try:

    while True:
        try:

            grabbed, original = camera.read()

            if grabbed == True:

                frame = original

                frame = imutils.resize(
                    frame,
                    width=int(config("FRAME_WIDTH")),
                    height=int(config("FRAME_HEIGHT")),
                )

                if int(config("FLIP_FRAME")) == 1:
                    frame = cv2.flip(frame, 1)

                frame = imutils.rotate(frame, int(config("FRAME_ANGLE")))

                if int(config("WHITE_BALANCE")) == 1:
                    frame = functions.white_balance(frame)

                if int(config("FILTER_FRAME")) == 1:
                    hsv_mask = functions.mask_color(frame, (hsv_lower), (hsv_upper))
                    result, x, y, w, h = functions.vision(hsv_mask, cascade_classifier)

                else:
                    result, x, y, w, h = functions.vision(frame, cascade_classifier)

                d = functions.current_distance(kpw, kd, kw, w)
                r = functions.calculate_rotation(int(config("FRAME_WIDTH")), x, w)
                b = functions.is_detected(d)

                try:
                    d = round(d, 2)
                    r = round(r, 2)
                except Exception:
                    pass

                table.putString("X", x)
                table.putString("Y", y)
                table.putString("W", w)
                table.putString("H", h)
                table.putString("D", d)
                table.putString("R", r)
                table.putString("B", b)

                if int(config("PRINT_VALUES")) == 1:
                    print(f"X: {x} Y: {y} W: {w} H: {h} D: {d} R: {r} B: {b}")

                if int(config("SHOW_FRAME")) == 1:
                    cv2.imshow("Result", functions.crosshair(result))
                    cv2.waitKey(1)

                if int(config("STREAM_FRAME")) == 1:
                    encoded, buffer = cv2.imencode(
                        ".jpg", functions.crosshair(original, camera)
                    )
                    footage_socket.send(buffer)

            else:
                try:
                    camera = functions.os_action()
                except Exception:
                    pass

        except KeyboardInterrupt:
            break

    try:
        flask_popen.kill()
    except AttributeError:
        pass

    camera.release()
    cv2.destroyAllWindows()

except Exception as e:
    print(e)

    try:
        flask_popen.kill()
        camera.release()
        cv2.destroyAllWindows()
    except AttributeError:
        pass
