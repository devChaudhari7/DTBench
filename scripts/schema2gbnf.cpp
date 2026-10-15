#include "json-schema-to-grammar.h"
#include <fstream>
#include <iostream>
#include <sstream>
int main(int argc, char ** argv) {
    if (argc < 2) { std::cerr << "usage: schema2gbnf schema.json\n"; return 1; }
    std::ifstream f(argv[1]);
    std::stringstream ss;
    ss << f.rdbuf();
    common_json schema = common_json::parse(ss.str());
    std::cout << json_schema_to_grammar(schema, true);
    return 0;
}
