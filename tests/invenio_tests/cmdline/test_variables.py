from pathlib import Path

from click.testing import CliRunner

runner = CliRunner()


async def test_variables(nrp_repository_config, run_cmdline_and_check):
    Path(".nrp/variables.json").unlink(missing_ok=True)
    run_cmdline_and_check(
        ["set", "variable", "blah", "MyVarContent", "MyVarContent1"],
        """
        Added variable blah -> MyVarContent
                               MyVarContent1
        """,
    )
    run_cmdline_and_check(
        ["list", "variables"],
        """
        Variables              
                            
        Name   Values        
        blah   MyVarContent 
               MyVarContent1
    """,
    )
    run_cmdline_and_check(
        ["set", "variable", "blah", "MyVarContent"],
        """
        Added variable blah -> MyVarContent
        """,
    )
    run_cmdline_and_check(
        ["get", "variable", "blah"],
        """
        MyVarContent
        """,
    )
    run_cmdline_and_check(
        ["remove", "variable", "blah"],
        """
        Removed variable blah
        """,
    )    
    run_cmdline_and_check(
        ["list", "variables"],
        """
        Variables        
                        
        Name   Values  
        ─────────────── 
        """,
    )
