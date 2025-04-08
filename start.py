from multiprocessing import Process
import luke
import leia
import yoda
import han_solo
import c3po

def start_agent(target, name):
    print(f"🔹 Iniciando agente: {name}")
    return Process(target=target)

if __name__ == "__main__":
    agents = [
        start_agent(luke.listen_for_commands, "Luke"),
        start_agent(leia.listen_for_commands, "Leia"),
        start_agent(yoda.listen_for_commands, "Yoda"),
        start_agent(han_solo.listen_for_commands, "Han Solo"),
        start_agent(c3po.listen_for_commands, "C-3PO"),
    ]

    for agent in agents:
        agent.start()

    for agent in agents:
        agent.join()
