with import <nixpkgs> { };

let
  pkgs1 = import <nixpkgs> {};
in

pkgs1.python3Packages.buildPythonPackage rec {
  name = "crawler";
  version = "0.0.1";

  buildInputs = [ ] ;

  propagatedBuildInputs = with pkgs1.python3Packages; [
    beautifulsoup4
  ];

}
