from json import dumps


def save_config(owl):
    try:
        with open("./config.py", "w") as f:
            f.write("ROUTEROS_IP = '{}'\n".format(owl.ROUTEROS_IP))
            f.write("ROUTEROS_USER = '{}'\n".format(owl.ROUTEROS_USER))
            f.write("ROUTEROS_PASSWORD = '{}'\n".format(owl.ROUTEROS_PASSWORD))
            f.write("RADIO_NAME = '{}'\n".format(owl.RADIO_NAME))
            f.write("CORR_OWL_IP = '{}'\n".format(owl.CORR_OWL_IP))
            f.close()
    except Exception as e:
        print('Error writing config.py:', e)


def save_config_offset(owl):
    try:
        with open("./config_offset.py", "w") as f:
            # f.write("AZIM_OFFSET = {}\n".format(dumps(owl.azim.mover.offset)))
            f.write("AZIM_OFFSET = 0.0\n")
            f.write("ELEV_OFFSET = {}\n".format(dumps(owl.elev.mover.offset)))
            f.close()
    except Exception as e:
        print('Error writing config_offset.py:', e)


def save_config_search(owl):
    try:
        with open("./config_search.py", "w") as f:
            f.write("AZIM_MAX_SEARCH = {}\n".format(dumps(owl.azim.max_search)))
            f.write("AZIM_MIN_SEARCH = {}\n".format(dumps(owl.azim.min_search)))
            f.write("ELEV_MAX_SEARCH = {}\n".format(dumps(owl.elev.max_search)))
            f.write("ELEV_MIN_SEARCH = {}\n".format(dumps(owl.elev.min_search)))
            f.close()
    except Exception as e:
        print('Error writing config_search.py:', e)


def save_config_PID(owl):
    try:
        with open("./config_PID.py", "w") as f:
            f.write("owl_azim_mover_pid_tunings = {}\n".format(dumps(owl.azim.mover.pid.tunings)))
            f.write("owl_azim_mover_pid_output_limits = {}\n".format(dumps(owl.azim.mover.pid.output_limits)))
            f.write("owl_azim_mover_pid_output_pads = {}\n\n".format(dumps(owl.azim.mover.pid.output_pads)))

            f.write("owl_elev_mover_pid_tunings = {}\n".format(dumps(owl.elev.mover.pid.tunings)))
            f.write("owl_elev_mover_pid_output_limits = {}\n".format(dumps(owl.elev.mover.pid.output_limits)))
            f.write("owl_elev_mover_pid_output_pads = {}\n".format(dumps(owl.elev.mover.pid.output_pads)))
            f.close()
    except Exception as e:
        print('Error writing config_PID.py:', e)
