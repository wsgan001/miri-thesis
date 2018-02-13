/*--------------------------------------------------------------------
  (C) Copyright 2006-2015 Barcelona Supercomputing Center
                          Centro Nacional de Supercomputacion
  
  This file is part of Mercurium C/C++ source-to-source compiler.
  
  See AUTHORS file in the top level directory for information
  regarding developers and contributors.
  
  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 3 of the License, or (at your option) any later version.
  
  Mercurium C/C++ source-to-source compiler is distributed in the hope
  that it will be useful, but WITHOUT ANY WARRANTY; without even the
  implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
  PURPOSE.  See the GNU Lesser General Public License for more
  details.
  
  You should have received a copy of the GNU Lesser General Public
  License along with Mercurium C/C++ source-to-source compiler; if
  not, write to the Free Software Foundation, Inc., 675 Mass Ave,
  Cambridge, MA 02139, USA.
--------------------------------------------------------------------*/

#include "loop-visitor.hpp"
#include "tl-nodecl.hpp"
#include "tl-nodecl-utils.hpp"
#include "tl-nodecl-visitor.hpp"
#include "tl-source.hpp"

// On every new nested level, EXTRAE_LOOPEVENT will be
// increment by one.
#define EXTRAE_LOOPEVENT 99000000
#define EXTRAE_ITEREVENT 99100000
#define EXTRAE_EXITEVENT 0

unsigned long long int loop_nested_level;

namespace TL {
    // This is the visitor used by the run method of this new phase
    // Heritage from ExhaustiveVisitor: This class visits all nodes of the
    // tree (representation of source code, output of frontend) in a recursive
    // manner.

    void new_unsigned_variable(TL::Scope context, std::string name, 
            unsigned int i)
    {
        // -- tl-omp-base.cpp:3633 --
        TL::Symbol new_symbol = context.new_symbol(name);
        new_symbol.get_internal_symbol()->kind = SK_VARIABLE;
        new_symbol.set_type(TL::Type::get_unsigned_long_long_int_type());
        symbol_entity_specs_set_is_user_declared(
                new_symbol.get_internal_symbol(), 1);

        Source init_value; init_value << i;
        new_symbol.set_value(init_value.parse_expression(context));
        context.insert_symbol(new_symbol);
    }

    class LoopsVisitor : public Nodecl::ExhaustiveVisitor<void>
    {
        public:
            // Executed before visit child nodes
            virtual void visit_pre(const Nodecl::ForStatement &node)
            {
                // It can be the loop-id for the moment.
                // ALERT: Two loops from different files can have the same line
                unsigned int loop_id = node.get_line();

                Source src_loop_init;
                src_loop_init 
                    <<      "Extrae_eventandcounters("
                    <<          (EXTRAE_LOOPEVENT+loop_nested_level)
                    <<          ", " << loop_id << ");";

                Source src_loop_fini;
                src_loop_fini 
                    <<      "Extrae_eventandcounters("
                    <<          (EXTRAE_LOOPEVENT+loop_nested_level)
                    <<          ", " << EXTRAE_EXITEVENT << ");";

                FORTRAN_LANGUAGE()
                {
                    // Parse in C
                    Source::source_language = SourceLanguage::C;
                }

                Nodecl::NodeclBase node_loop_init = src_loop_init.parse_statement(node);
                Nodecl::NodeclBase node_loop_fini = src_loop_fini.parse_statement(node);

                FORTRAN_LANGUAGE()
                {
                    Source::source_language = SourceLanguage::Current;
                }

                node.prepend_sibling(node_loop_init);
                node.append_sibling(node_loop_fini);
                
                loop_nested_level += 1;
            }

            // Executed after visit child nodes
            virtual void visit_post(const Nodecl::ForStatement &node)
            {
                unsigned int loop_id = node.get_line();
                loop_nested_level -= 1;

                //TL::ForStatement for_statement(node);
                //TL::Symbol ind_var = for_statement.get_induction_variable();
                //std::string ind_var_name = ind_var.get_name();
                
                std::string new_it_var_name = std::string("__mercurium_it_id_")
                    + std::to_string(loop_id);

                new_unsigned_variable(node.retrieve_context(), new_it_var_name, 0);

                Nodecl::NodeclBase new_statement;
                Source src;
                src
                    << "{"
                    <<      "Extrae_eventandcounters("
                    <<          (EXTRAE_ITEREVENT+loop_nested_level)
                    <<          ", ++" << new_it_var_name  << ");"
                    <<      statement_placeholder(new_statement)
                    <<      "Extrae_eventandcounters("
                    <<          (EXTRAE_ITEREVENT+loop_nested_level)
                    <<          "," << EXTRAE_EXITEVENT << ");"
                    << "}";

                Nodecl::NodeclBase generated_code = src.parse_statement(node);
                new_statement.replace(node.get_statement());
                node.get_statement().replace(generated_code);
            }
    };


    VisitorLoopPhase::VisitorLoopPhase()
    {
        set_phase_name("Loop visitor");
        set_phase_description("This phase shows information about loops");

        loop_nested_level = 0;
    }
    VisitorLoopPhase::~VisitorLoopPhase()
    {
    }
    void VisitorLoopPhase::run(TL::DTO& dto)
    {
        Nodecl::NodeclBase top_level = 
            *std::static_pointer_cast<Nodecl::NodeclBase>(dto["nodecl"]);

        // Nested level also has to be done by means of 
        // user variable. This is because loops from diferent files
        // can be nested.
        //
        new_unsigned_variable(top_level.retrieve_context(),"__mercurium_loopid", 1);

        LoopsVisitor loops_visitor;
        loops_visitor.walk(top_level);
    }

    
}

EXPORT_PHASE(TL::VisitorLoopPhase);