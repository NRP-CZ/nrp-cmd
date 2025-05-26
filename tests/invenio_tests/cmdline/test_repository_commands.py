import pytest
from click.testing import CliRunner
from yarl import URL

from nrp_cmd.cli import app
from nrp_cmd.config import Config

runner = CliRunner()


def test_add_local_repository(empty_config, token_a):
    assert empty_config.repositories == []

    result = runner.invoke(
        app,
        [
            "add",
            "repository",
            "--no-verify-tls",
            "--no-launch-browser",
            "https://127.0.0.1:5000",
            "local",
        ],
        input=f"\n{token_a}\n",
        env={"NRP_CMD_CONFIG_PATH": str(empty_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert "Adding repository https://127.0.0.1:5000 with alias local" in stdout
    assert "I will try to open the following url in your browser:" in stdout
    assert "https://127.0.0.1:5000/account/settings/applications/tokens/new" in stdout
    assert "Added repository local -> https://127.0.0.1:5000" in stdout
    assert result.exit_code == 0
    config = Config.from_file(empty_config._config_file_path)
    assert len(config.repositories) == 1
    assert config.repositories[0].alias == "local"
    assert config.repositories[0].url == URL("https://127.0.0.1:5000")
    assert config.repositories[0].token == token_a
    assert not config.repositories[0].verify_tls


def test_repository_listing(nrp_repository_config, run_cmdline_and_check):
    run_cmdline_and_check(
        ["list", "repositories"],
        """
    local https://127.0.0.1:5000 ✓
    zenodo https://www.zenodo.org
                     """,
    )


def test_repository_listing_details(nrp_repository_config, run_cmdline_and_check):
    run_cmdline_and_check(
        ["list", "repositories", "--verbose"],
        """
Repository 'local'                              
                                                
  URL                   https://127.0.0.1:5000  
  Token                 ***                     
  TLS Verify            skip                    
  Retry Count           5                       
  Retry After Seconds   10                      
  Default               ✓                         
                                                
Repository 'zenodo'                             
                                                
  URL                   https://www.zenodo.org  
  Token                 anonymous               
  TLS Verify            ✓                       
  Retry Count           5                       
  Retry After Seconds   10                      
  Default                                                  
                     """,
    )


def test_repository_listing_details_json(nrp_repository_config, run_cmdline_and_check):
    assert nrp_repository_config.repositories[0].info is None
    assert nrp_repository_config.repositories[1].info is None
    run_cmdline_and_check(
        ["list", "repositories", "--verbose", "--output-format", "json"],
        """
[
    {
        "alias": "local",
        "url": "https://127.0.0.1:5000",
        "token": "***",
        "verify_tls": false,
        "retry_count": 5,
        "retry_after_seconds": 10,
        "info": null,
        "default": true
    },
    {
        "alias": "zenodo",
        "url": "https://www.zenodo.org",
        "token": "anonymous",
        "verify_tls": true,
        "retry_count": 5,
        "retry_after_seconds": 10,
        "info": null,
        "default": false
    }
]
""",
    )


def test_repository_listing_details_yaml(nrp_repository_config, run_cmdline_and_check):
    assert nrp_repository_config.repositories[0].info is None
    assert nrp_repository_config.repositories[1].info is None

    run_cmdline_and_check(
        ["list", "repositories", "--verbose", "--output-format", "yaml"],
        """
- alias: local
  default: true
  info: null
  retry_after_seconds: 10
  retry_count: 5
  token: '***'
  url: https://127.0.0.1:5000
  verify_tls: false
- alias: zenodo
  info: null
  retry_after_seconds: 10
  retry_count: 5
  token: anonymous
  url: https://www.zenodo.org
  verify_tls: true
""",
    )


def test_repository_select(nrp_repository_config):
    result = runner.invoke(
        app,
        ["select", "repository", "local"],
        catch_exceptions=False,
        env={"NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert 'Selected repository "local"' in stdout
    config = Config.from_file(nrp_repository_config._config_file_path)
    assert config.default_alias == "local"

    result = runner.invoke(
        app,
        ["select", "repository", "zenodo"],
        catch_exceptions=False,
        env={"NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert 'Selected repository "zenodo"' in stdout
    config = Config.from_file(nrp_repository_config._config_file_path)
    assert config.default_alias == "zenodo"


def test_repository_enable_disable(nrp_repository_config):
    result = runner.invoke(
        app,
        ["enable", "repository", "local"],
        catch_exceptions=False,
        env={"NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert 'Enabled repository "local"' in stdout
    config = Config.from_file(nrp_repository_config._config_file_path)
    assert config.get_repository("local").enabled

    local_repo = next(repo for repo in config.repositories if repo.alias == "local")
    for_url = config.get_repository_from_url(local_repo.url)
    assert for_url is local_repo

    result = runner.invoke(
        app,
        ["disable", "repository", "local"],
        catch_exceptions=False,
        env={"NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert 'Disabled repository "local"' in stdout
    config = Config.from_file(nrp_repository_config._config_file_path)

    with pytest.raises(ValueError, match="Repository with alias 'local' is disabled"):
        config.get_repository("local")

    assert config.get_repository("zenodo").enabled

    local_repo = next(repo for repo in config.repositories if repo.alias == "local")
    for_url = config.get_repository_from_url(local_repo.url)
    assert for_url is not local_repo


def test_repository_remove(nrp_repository_config):
    config = Config.from_file(nrp_repository_config._config_file_path)
    assert len(config.repositories) == 3
    result = runner.invoke(
        app,
        ["remove", "repository", "local"],
        catch_exceptions=False,
        env={"NRP_CMD_CONFIG_PATH": str(nrp_repository_config._config_file_path)},
    )
    stdout = result.stdout
    print(stdout)
    assert 'Removed repository "local"' in stdout
    config = Config.from_file(nrp_repository_config._config_file_path)
    assert len(config.repositories) == 2
    assert config.get_repository("zenodo")

    with pytest.raises(KeyError, match="Repository with alias 'local' not found"):
        config.get_repository("local")


def test_repository_describe_local(nrp_repository_config, run_cmdline_and_check):
    run_cmdline_and_check(
        ["describe", "repository", "--refresh", "local"],
        {"COLUMNS": "200"},
        """
Repository 'local'                                               
                                                                 
  Name                  Test repository for nrp-cmd              
  URL                   https://127.0.0.1:5000                   
  Token                 ***                                      
  TLS Verify            skip                                     
  Retry Count           5                                        
  Retry After Seconds   10                                       
  Default               ✓                                      
  Version               local development                        
  Transfers             F, L, M, R                               
  Records url           https://127.0.0.1:5000/api/search/       
  User drafts           https://127.0.0.1:5000/api/user/search/  
                                                                 
Model 'simple'                                                                                                 
                                                                                                               
  Name                    simple                                                                               
  Description                                                                                                  
  Version                 1.0.0                                                                                
  Features                requests, drafts, files                                                              
  HTML                    https://127.0.0.1:5000/simple/                                                       
  Model Schema            https://127.0.0.1:5000/.well-known/repository/models/simple                          
  Published Records URL   https://127.0.0.1:5000/api/simple/                                                   
  User Records URL        https://127.0.0.1:5000/api/user/simple/                                              
  Content-Type            application/json                                                                     
                          Internal json serialization of Simple                                                
                          This content type is serving this model's native format as described on model link.  
      Schema              https://127.0.0.1:5000/.well-known/repository/schema/simple-1.0.0.json               
      Can Export          ✓                                                                                    
      Can Deposit         ✓                                                                                    
  Content-Type            application/vnd.inveniordm.v1+json                                                   
                          Native UI JSON                                                   
                                                                                                               
      Schema              None                                                                                 
      Can Export          ✓                                                                                    
      Can Deposit                                                                                              
                                                                                                               
Model 'affiliations'                                                                           
                                                                                               
  Name                    Affiliations                                                         
  Description             Vocabulary for Affiliations                                          
  Version                 unknown                                                              
  Features                rdm, vocabulary                                                      
  HTML                    None                                                                 
  Model Schema            None                                                                 
  Published Records URL   https://127.0.0.1:5000/api/affiliations                              
  User Records URL        None                                                                 
  Content-Type            application/json                                                     
                          Invenio RDM JSON                                                     
                          Vocabulary JSON                                                      
      Schema              https://127.0.0.1:5000/schemas/affiliations/affiliation-v1.0.0.json  
      Can Export          ✓                                                                    
      Can Deposit                                                                              
                                                                                               
Model 'awards'                                                                     
                                                                                   
  Name                    Awards                                                   
  Description             Vocabulary for Awards                                    
  Version                 unknown                                                  
  Features                rdm, vocabulary                                          
  HTML                    None                                                     
  Model Schema            None                                                     
  Published Records URL   https://127.0.0.1:5000/api/awards                        
  User Records URL        None                                                     
  Content-Type            application/json                                         
                          Invenio RDM JSON                                         
                          Vocabulary JSON                                          
      Schema              https://127.0.0.1:5000/schemas/awards/award-v1.0.0.json  
      Can Export          ✓                                                        
      Can Deposit                                                                  
                                                                                   
Model 'funders'                                                                      
                                                                                     
  Name                    Funders                                                    
  Description             Vocabulary for Funders                                     
  Version                 unknown                                                    
  Features                rdm, vocabulary                                            
  HTML                    None                                                       
  Model Schema            None                                                       
  Published Records URL   https://127.0.0.1:5000/api/funders                         
  User Records URL        None                                                       
  Content-Type            application/json                                           
                          Invenio RDM JSON                                           
                          Vocabulary JSON                                            
      Schema              https://127.0.0.1:5000/schemas/funders/funder-v1.0.0.json  
      Can Export          ✓                                                          
      Can Deposit                                                                    
                                                                                     
Model 'subjects'                                                                       
                                                                                       
  Name                    Subjects                                                     
  Description             Vocabulary for Subjects                                      
  Version                 unknown                                                      
  Features                rdm, vocabulary                                              
  HTML                    None                                                         
  Model Schema            None                                                         
  Published Records URL   https://127.0.0.1:5000/api/subjects                          
  User Records URL        None                                                         
  Content-Type            application/json                                             
                          Invenio RDM JSON                                             
                          Vocabulary JSON                                              
      Schema              https://127.0.0.1:5000/schemas/subjects/subject-v1.0.0.json  
      Can Export          ✓                                                            
      Can Deposit                                                                      
                                                                                       
Model 'names'                                                                    
                                                                                 
  Name                    Names                                                  
  Description             Vocabulary for Names                                   
  Version                 unknown                                                
  Features                rdm, vocabulary                                        
  HTML                    None                                                   
  Model Schema            None                                                   
  Published Records URL   https://127.0.0.1:5000/api/names                       
  User Records URL        None                                                   
  Content-Type            application/json                                       
                          Invenio RDM JSON                                       
                          Vocabulary JSON                                        
      Schema              https://127.0.0.1:5000/schemas/names/name-v1.0.0.json  
      Can Export          ✓                                                      
      Can Deposit                                                                
                                                                                 
Model 'affiliations-vocab'                                                                     
                                                                                               
  Name                    Writable Affiliations                                                
  Description             Vocabulary for Writable Affiliations                                 
  Version                 unknown                                                              
  Features                rdm, vocabulary                                                      
  HTML                    None                                                                 
  Model Schema            None                                                                 
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/affiliations-vocab           
  User Records URL        None                                                                 
  Content-Type            application/json                                                     
                          Invenio RDM JSON                                                     
                          Vocabulary JSON                                                      
      Schema              https://127.0.0.1:5000/schemas/affiliations/affiliation-v1.0.0.json  
      Can Export          ✓                                                                    
      Can Deposit         ✓                                                                    
                                                                                               
Model 'awards-vocab'                                                               
                                                                                   
  Name                    Writable Awards                                          
  Description             Vocabulary for Writable Awards                           
  Version                 unknown                                                  
  Features                rdm, vocabulary                                          
  HTML                    None                                                     
  Model Schema            None                                                     
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/awards-vocab     
  User Records URL        None                                                     
  Content-Type            application/json                                         
                          Invenio RDM JSON                                         
                          Vocabulary JSON                                          
      Schema              https://127.0.0.1:5000/schemas/awards/award-v1.0.0.json  
      Can Export          ✓                                                        
      Can Deposit         ✓                                                        
                                                                                   
Model 'funders-vocab'                                                                
                                                                                     
  Name                    Writable Funders                                           
  Description             Vocabulary for Writable Funders                            
  Version                 unknown                                                    
  Features                rdm, vocabulary                                            
  HTML                    None                                                       
  Model Schema            None                                                       
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/funders-vocab      
  User Records URL        None                                                       
  Content-Type            application/json                                           
                          Invenio RDM JSON                                           
                          Vocabulary JSON                                            
      Schema              https://127.0.0.1:5000/schemas/funders/funder-v1.0.0.json  
      Can Export          ✓                                                          
      Can Deposit         ✓                                                          
                                                                                     
Model 'subjects-vocab'                                                                 
                                                                                       
  Name                    Writable Subjects                                            
  Description             Vocabulary for Writable Subjects                             
  Version                 unknown                                                      
  Features                rdm, vocabulary                                              
  HTML                    None                                                         
  Model Schema            None                                                         
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/subjects-vocab       
  User Records URL        None                                                         
  Content-Type            application/json                                             
                          Invenio RDM JSON                                             
                          Vocabulary JSON                                              
      Schema              https://127.0.0.1:5000/schemas/subjects/subject-v1.0.0.json  
      Can Export          ✓                                                            
      Can Deposit         ✓                                                            
                                                                                       
Model 'names-vocab'                                                              
                                                                                 
  Name                    Writable Names                                         
  Description             Vocabulary for Writable Names                          
  Version                 unknown                                                
  Features                rdm, vocabulary                                        
  HTML                    None                                                   
  Model Schema            None                                                   
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/names-vocab    
  User Records URL        None                                                   
  Content-Type            application/json                                       
                          Invenio RDM JSON                                       
                          Vocabulary JSON                                        
      Schema              https://127.0.0.1:5000/schemas/names/name-v1.0.0.json  
      Can Export          ✓                                                      
      Can Deposit         ✓                                                      
                                                                                 
Model 'languages'                                                                             
                                                                                              
  Name                    languages                                                           
  Description             Vocabulary for languages                                            
  Version                 unknown                                                             
  Features                rdm, vocabulary                                                     
  HTML                    None                                                                
  Model Schema            None                                                                
  Published Records URL   https://127.0.0.1:5000/api/vocabularies/languages                   
  User Records URL        None                                                                
  Content-Type            application/json                                                    
                          Invenio RDM JSON                                                    
                          Vocabulary JSON                                                     
      Schema              https://127.0.0.1:5000/schemas/vocabularies/vocabulary-v1.0.0.json  
      Can Export          ✓                                                                   
      Can Deposit         ✓                                                                   
                     """,
    )
