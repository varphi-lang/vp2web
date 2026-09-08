import json
from varphi_devkit import VarphiCompiler, BuiltinSymbol, Character
from vp2py.lib.model import State, TuringMachine, Tape

class VarphiInMemoryCompiler(VarphiCompiler):
    """
    Compiles Varphi directly into Python objects.
    
    Returns a tuple containing:
        - The number of tapes
        - The State object corresponding to the initial state
        - The state registry (a dict mapping state names to State objects)
    """
    def _generate_compiled_program(self) -> tuple[int, State, dict[str, State]]:
        state_registry = {name: State(name) for name in self.states}
        
        for state_name, transitions in self.ir.items():
            for t in transitions:
                state_registry[state_name].add_transition(t)
                
        return self._tape_count, state_registry[self.initial_state], state_registry

class VarphiWebSession:
    """Model for the JS frontend."""
    k: int
    initial_state: str | None
    state_registry: dict[str, State] | None
    tm: TuringMachine | None
    blank_char: str

    def __init__(self) -> None:
        self.k = 0
        self.initial_state = None
        self.state_registry = None
        self.tm = None
        self.blank_char = "_"

    def compile(self, source_code: str) -> str:
        """
        Compile a Varphi program and initialize some internal values of this instance:
            - k
            - initial_state
            - state_registry
        """
        try:
            compiler = VarphiInMemoryCompiler()
            self.k, self.initial_state, self.state_registry = compiler.compile(source_code)
            return json.dumps({"success": True, "k": self.k})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def init_machine(self, inputs: list[str], blank_char: str) -> str:
        """
        Initialize the tapes with user input and return the initial state 
        after creating the Turing machine.
        """
        self.blank_char = blank_char
        tapes = []
        
        for inp in inputs:
            parsed_tape = []
            for char in inp:
                if char == self.blank_char:
                    parsed_tape.append(BuiltinSymbol.BLANK)
                else:
                    parsed_tape.append(Character(char))
            tapes.append(Tape(parsed_tape))

        # Create the Turing machine object
        self.tm = TuringMachine(self.k, tuple(tapes), self.initial_state, self.state_registry)
        return self.get_state()

    def step(self) -> str:
        if self.tm._next_transition is not None:  # Machine has a transition armed
            # Execute the transition
            self.tm.step()
            
        # get_state will call peek() to arm the next transition and update the UI
        return self.get_state()

    def get_state(self) -> str:
        """
        Get the state of the TM as JSON.
        - "state": The name of the current state
        - "tapes": A list containing:
            - "string": The active portion of the tape.
            - "head_position": The 0-based index of the head within "string".
        - "halted": A boolean for whether the machine has halted
        - "line_number": The transition line number matching the current situation
        """
        if not self.tm:
            return json.dumps({"error": "Machine not initialized"})
            
        is_halted = not self.tm.peek()
        
        tapes_data = []
        for head in self.tm.heads:
            tape = head.tape
            if tape._min_idx is None:  # Tape is all BLANK
                string = ""
                relative_head = 0
            else:
                actual_min = tape._min_idx
                actual_max = tape._max_idx
                chars = []
                for i in range(actual_min, actual_max + 1):
                    val = tape._tape.get(i, BuiltinSymbol.BLANK)
                    chars.append(self.blank_char if val == BuiltinSymbol.BLANK else val.value)
                string = "".join(chars)
                # Calculate the relative position of the head inside the string
                # This is because min_idx can be negative
                relative_head = head.index - actual_min
                
            tapes_data.append({
                "string": string,
                "head_position": relative_head,
            })
            
        next_line = self.tm._next_transition.line_number if self.tm._next_transition else None
            
        return json.dumps({
            "state": self.tm.state.name,
            "tapes": tapes_data,
            "halted": is_halted,
            "line_number": next_line
        })