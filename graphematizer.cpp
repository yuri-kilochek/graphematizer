#include <iostream>
#include <fstream>
#include <stdexcept>
#include <string>
#include <sstream>
#include <algorithm>
#include <vector>

#include <pegasus.hpp>

struct unable_to_open_file
    : std::runtime_error
{
    std::string const pathname;

    unable_to_open_file(std::string const& pathname)
        : std::runtime_error("::unable_to_open_file(\"" + pathname + "\")")
        , pathname(pathname)
    {}
};

static std::u32string read_utf8_file(std::string const& pathname) {
    std::u32string text;

    std::ifstream ifstream(pathname.c_str());

    if (!ifstream.is_open()) {
        throw unable_to_open_file(pathname);
    }

    std::copy(pegasus::utf8_decoder(std::istreambuf_iterator<char>(ifstream)),
              pegasus::utf8_decoder(std::istreambuf_iterator<char>()),
              std::back_inserter(text));

    ifstream.close();

    return text;
}

static void write_utf8_file(std::string const& pathname, std::u32string const& text) {
    std::ofstream ofstream(pathname.c_str());

    if (!ofstream.is_open()) {
        throw unable_to_open_file(pathname);
    }

    std::copy(text.begin(), text.end(),
              pegasus::utf8_encoder(std::ostreambuf_iterator<char>(ofstream)));

    ofstream.close();
}

template <typename T>
static inline std::string to_string(T const& x) {
    std::stringstream ss;
    ss << x;
    return ss.str();
}

namespace graphematics {
    using namespace pegasus;

    auto drop_ch = [](take<char32_t>) {};
    auto drop_str = [](take<std::u32string>) {};
    auto append_ch = [](edit<std::u32string> s, take<char32_t> c) { *s += *c; };
    auto append_str = [](edit<std::u32string> a, take<std::u32string> b) { *a += std::move(*b); };
    auto put_empty_vector = [](put<std::vector<std::u32string>>) {};
    auto drop_vector = [](take<std::vector<std::u32string>>) {};
    auto append_grapheme = [](edit<std::vector<std::u32string>> gs, take<std::u32string> g) {
        gs->push_back(U"n " + *g);
    };
    auto make_last_end = [](edit<std::vector<std::u32string>> gs) {
        if (!gs->empty()) {
            gs->back().front() = U'e';
        }
    };

    auto ws = estr >> +(chs(U" \n") >> act(append_ch)) >> act(drop_str);

    auto digit = chr(U'0', U'9');

    auto number = estr >>
                  +(digit >> act(append_ch)) >>
                  ~(chs(U".,") >> act(append_ch) >>
                    +(digit >> act(append_ch))) >>
                  act(append_grapheme);

    auto number_range = number >>
                        estr >> chs(U"–-—") >> act(append_ch) >> act(append_grapheme) >>
                        number;

    auto list_index = act(make_last_end) >>
                      number >>
                      estr >> chs(U".)") >> act(append_ch) >> act(append_grapheme);

    auto punctuation =                       str(U"—") >> act(append_grapheme) |
                                             str(U",") >> act(append_grapheme) |
                                             str(U";") >> act(append_grapheme) >> act(make_last_end) |
                                             str(U":") >> act(append_grapheme) |
                                             str(U"…") >> act(append_grapheme) >> act(make_last_end) |
                                             str(U"...") >> act(append_grapheme) >> act(make_last_end) |
                                             str(U".") >> act(append_grapheme) >> act(make_last_end) |
                                             str(U"!") >> act(append_grapheme) >> act(make_last_end) |
                                             str(U"?") >> act(append_grapheme) >> act(make_last_end) |
                       act(make_last_end) >> str(U"•") >> act(append_grapheme) |
                                             str(U"«") >> act(append_grapheme) |
                                             str(U"»") >> act(append_grapheme) |
                                             str(U"\"") >> act(append_grapheme) |
                                             str(U"(") >> act(append_grapheme) |
                                             str(U")") >> act(append_grapheme) |
                                             str(U"[") >> act(append_grapheme) |
                                             str(U"]") >> act(append_grapheme) |
                                             str(U"//") >> act(append_grapheme) |
                                             str(U"/") >> act(append_grapheme) |
                                             str(U"°") >> act(append_grapheme) |
                                             str(U"+") >> act(append_grapheme) |
                                             str(U"%") >> act(append_grapheme) |
                                             str(U"&") >> act(append_grapheme);

    auto letter_block = estr >>
                        +(!ws >> !(act(put_empty_vector) >> punctuation >> act(drop_vector)) >> ach >> act(append_ch)) >>
                        act(append_grapheme);

    auto grapheme = ~ws >> (number_range >> !(chs(U"–-") >> act(drop_ch)) |
                            list_index |
                            number >> !(chs(U"–-") >> act(drop_ch)) |
                            punctuation |
                            letter_block);

    auto bom = ch(0xFEFF) >> act(drop_ch);

    auto text = ~bom >> act(put_empty_vector) >> *grapheme >> act(make_last_end);
}

int main(int argc, char const* argv[]) {
    if (argc != 3) {
        std::cerr << "Invalid arguments. Usage:\n"
                  << "\tgraphematics <plaintext> <graphemes>";
        return 1;
    }

    std::string plaintext_path = argv[1];
    std::string graphemes_path = argv[2];

    using namespace graphematics;

    try {
        auto plaintext = read_utf8_file(plaintext_path);
        try {
            auto graphemes = parse(text, plaintext);
            std::u32string buffer;
            for (auto&& g : graphemes) {
                buffer += g + U'\n';
            }
            write_utf8_file(graphemes_path, buffer);
        } catch (failure &) {
            std::cerr << "Unable to graphematize " << plaintext_path;
            return 1;
        }
    } catch (unable_to_open_file& e) {
        std::cerr << "Unable to open " << e.pathname;
        return 1;
    }

    return 0;
}
