let
  np = import <nixpkgs> { };

  new-py = np.python3;

in
  with np;
    mkShell { buildInputs =
      [(new-py.withPackages (ps: with ps; [ ]))]; }

