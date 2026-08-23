import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  GitPullRequest, 
  Search, 
  Star, 
  GitFork, 
  GitBranch, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles,
  Layers,
  FolderGit2,
  Clock,
  Plus,
  Minus,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { Repo, PullRequest, Branch } from '../lib/types';
import { getRepos, getPullRequests, getBranches, createPullRequest, createVerifyJob, BACKEND_URL } from '../lib/api';

interface RepoSelectionScreenProps {
  onStartVerify: (jobId: string, repoFullName: string, prNumber: number) => void;
}

export const RepoSelectionScreen: React.FC<RepoSelectionScreenProps> = ({ onStartVerify }) => {
  const navigate = useNavigate();

  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('repo-1');
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [activeTab, setActiveTab] = useState<'prs' | 'branches'>('prs');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoadingRepos, setIsLoadingRepos] = useState<boolean>(true);
  const [isLoadingPRs, setIsLoadingPRs] = useState<boolean>(false);
  const [isLoadingBranches, setIsLoadingBranches] = useState<boolean>(false);
  const [isStartingJob, setIsStartingJob] = useState<number | string | null>(null);

  // Create PR Modal State
  const [showCreatePRModal, setShowCreatePRModal] = useState<boolean>(false);
  const [newPRHead, setNewPRHead] = useState<string>('');
  const [newPRBase, setNewPRBase] = useState<string>('main');
  const [newPRTitle, setNewPRTitle] = useState<string>('');
  const [newPRBody, setNewPRBody] = useState<string>('');
  const [isCreatingPR, setIsCreatingPR] = useState<boolean>(false);
  const [createPRError, setCreatePRError] = useState<string | null>(null);

  const [customRepoInput, setCustomRepoInput] = useState<string>('');
  const [isAddingRepo, setIsAddingRepo] = useState<boolean>(false);
  const [activeUsername, setActiveUsername] = useState<string>('alien1611');

  useEffect(() => {
    async function loadInitialRepos() {
      setIsLoadingRepos(true);
      try {
        // Fetch active user
        fetch(`${BACKEND_URL}/api/auth/user`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data?.authenticated && data.username) {
              setActiveUsername(data.username);
            }
          })
          .catch(() => {});

        const repoList = await getRepos();
        setRepos(repoList);
        if (repoList.length > 0) {
          setSelectedRepoId(repoList[0].id);
        }
      } catch (err) {
        console.error('Failed to load repos:', err);
      } finally {
        setIsLoadingRepos(false);
      }
    }
    loadInitialRepos();
  }, []);

  const handleAddCustomRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanRepo = customRepoInput.trim().replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '');
    if (!cleanRepo || !cleanRepo.includes('/')) return;

    setIsAddingRepo(true);
    try {
      const parts = cleanRepo.split('/');
      const res = await fetch(`${BACKEND_URL}/api/repositories/${parts[0]}/${parts[1]}`);
      const newRepo: Repo = {
        id: `repo-${Date.now()}`,
        full_name: cleanRepo,
        description: res.ok ? (await res.json()).description || 'Custom GitHub Repository' : 'Custom GitHub Repository',
        stars: 0,
        forks: 0,
        language: 'TypeScript',
        default_branch: 'main'
      };
      setRepos(prev => [newRepo, ...prev.filter(r => r.full_name !== cleanRepo)]);
      setSelectedRepoId(newRepo.id);
      setCustomRepoInput('');
    } catch (e) {
      const newRepo: Repo = {
        id: `repo-${Date.now()}`,
        full_name: cleanRepo,
        description: 'Custom GitHub Repository',
        stars: 0,
        forks: 0,
        language: 'TypeScript',
        default_branch: 'main'
      };
      setRepos(prev => [newRepo, ...prev.filter(r => r.full_name !== cleanRepo)]);
      setSelectedRepoId(newRepo.id);
      setCustomRepoInput('');
    } finally {
      setIsAddingRepo(false);
    }
  };

  const selectedRepo = repos.find(r => r.id === selectedRepoId);

  useEffect(() => {
    async function loadRepoData() {
      if (!selectedRepo) return;
      setIsLoadingPRs(true);
      setIsLoadingBranches(true);
      try {
        const [prList, branchList] = await Promise.all([
          getPullRequests(selectedRepo.full_name),
          getBranches(selectedRepo.full_name)
        ]);
        setPullRequests(prList);
        setBranches(branchList);
        if (branchList.length > 0) {
          const nonMain = branchList.find(b => b.name !== 'main');
          setNewPRHead(nonMain ? nonMain.name : branchList[0].name);
        }
      } catch (err) {
        console.error('Failed to load repo data:', err);
      } finally {
        setIsLoadingPRs(false);
        setIsLoadingBranches(false);
      }
    }
    loadRepoData();
  }, [selectedRepoId, selectedRepo?.id, selectedRepo?.full_name]);

  const filteredRepos = repos.filter(r => 
    r.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleTriggerVerification = async (prOrBranchNumber: number | string) => {
    if (!selectedRepo) return;
    setIsStartingJob(prOrBranchNumber);

    const prNum = typeof prOrBranchNumber === 'number' ? prOrBranchNumber : 1;
    try {
      const response = await createVerifyJob({
        repo_full_name: selectedRepo.full_name,
        pr_number: prNum
      });
      onStartVerify(response.job_id, selectedRepo.full_name, prNum);
      navigate(`/verify/${response.job_id}`);
    } catch (err) {
      console.error('Failed to create verify job:', err);
      setIsStartingJob(null);
    }
  };

  const handleCreatePRSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepo || !newPRTitle.trim() || !newPRHead) return;

    setIsCreatingPR(true);
    setCreatePRError(null);

    try {
      const newPr = await createPullRequest(selectedRepo.full_name, {
        title: newPRTitle.trim(),
        head: newPRHead,
        base: newPRBase || 'main',
        body: newPRBody.trim() || undefined
      });

      // Reload PRs
      const updatedPRs = await getPullRequests(selectedRepo.full_name);
      setPullRequests(updatedPRs);
      setShowCreatePRModal(false);
      setActiveTab('prs');
      setNewPRTitle('');
      setNewPRBody('');
    } catch (err: any) {
      const errMsg = err instanceof Error ? err.message : String(err);
      if (errMsg.includes('already exists')) {
        // Automatically switch to PRs tab and refresh
        const updatedPRs = await getPullRequests(selectedRepo.full_name);
        setPullRequests(updatedPRs);
        setShowCreatePRModal(false);
        setActiveTab('prs');
      } else {
        setCreatePRError(errMsg);
      }
    } finally {
      setIsCreatingPR(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0D10] text-[#F2F1ED] py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b border-[#232A35] pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#F5A623] uppercase tracking-wider mb-1">
            <FolderGit2 className="w-4 h-4" />
            STATION 00 // INTAKE DOCK
          </div>
          <h1 className="font-['Big_Shoulders_Display'] text-4xl sm:text-5xl font-black uppercase text-[#F2F1ED]">
            SELECT REPOSITORY & PULL REQUEST
          </h1>
          <p className="text-sm text-[#8E96A0] mt-1">
            Choose any connected GitHub PR to run AST analysis, invariant verification, and adversarial fuzzing.
          </p>
        </div>

        {/* Search Bar & Workspace Switcher */}
        <div className="flex items-center gap-3">
          <Link
            to="/connect"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#14171D] hover:bg-[#1C222B] border border-[#2A3038] text-[#37E2C4] font-mono text-xs transition-all cursor-pointer"
            title="Switch Workspace or PAT Token"
          >
            <span>@{activeUsername} (Manage Auth)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>

          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 text-[#8E96A0] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search repositories..."
              className="w-full bg-[#14171D] border border-[#2A3038] rounded-md pl-9 pr-3 py-2 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#F5A623]"
            />
          </div>
        </div>
      </div>

      {/* Quick Add Custom Repo Bar */}
      <form onSubmit={handleAddCustomRepo} className="p-4 rounded-xl bg-[#14171D] border border-[#232A35] flex flex-col sm:flex-row items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-[#37E2C4] whitespace-nowrap">
          <Plus className="w-4 h-4" />
          <span>LOAD ANY REPOSITORY:</span>
        </div>
        <input 
          type="text"
          value={customRepoInput}
          onChange={(e) => setCustomRepoInput(e.target.value)}
          placeholder="e.g. alien1611/the-code-factory or owner/repo"
          className="flex-1 w-full bg-[#0B0D10] border border-[#2A3038] rounded-lg px-3.5 py-2 text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0] focus:outline-none focus:border-[#37E2C4]"
        />
        <button
          type="submit"
          disabled={isAddingRepo || !customRepoInput.trim()}
          className="w-full sm:w-auto px-4 py-2 rounded-lg bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono text-xs font-bold transition-all cursor-pointer disabled:opacity-50"
        >
          {isAddingRepo ? 'FETCHING REPOSITORY...' : 'FETCH REPOSITORY'}
        </button>
      </form>

      {/* Main Split: Left Repo List, Right PR List */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Repositories (4 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-[#8E96A0]">
            <div className="flex items-center gap-2">
              <span>CONNECTED REPOSITORIES ({filteredRepos.length})</span>
              <button 
                onClick={async () => {
                  setIsLoadingRepos(true);
                  try {
                    const list = await getRepos();
                    setRepos(list);
                    if (list.length > 0) setSelectedRepoId(list[0].id);
                  } finally {
                    setIsLoadingRepos(false);
                  }
                }}
                disabled={isLoadingRepos}
                title="Refresh Repositories from GitHub"
                className="p-1 hover:text-[#37E2C4] transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingRepos ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <Link to="/connect" className="text-[#37E2C4] hover:underline flex items-center gap-1">
              <span>@{activeUsername}</span>
            </Link>
          </div>

          <div className="space-y-3" data-testid="repo-list">
            {isLoadingRepos ? (
              <div className="p-8 text-center text-xs font-mono text-[#8E96A0] animate-pulse flex flex-col items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-[#37E2C4]" />
                <span>Loading repositories from GitHub...</span>
              </div>
            ) : filteredRepos.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-[#8E96A0] border border-[#232A35] rounded-md">
                No matching repositories found
              </div>
            ) : (
              filteredRepos.map((repo) => {
                const isSelected = repo.id === selectedRepoId;
                return (
                  <div
                    key={repo.id}
                    onClick={() => setSelectedRepoId(repo.id)}
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      isSelected 
                        ? 'bg-[#181C23] border-[#F5A623] shadow-[0_0_20px_rgba(245,166,35,0.15)]' 
                        : 'bg-[#14171D] border-[#2A3038] hover:bg-[#1C222B]'
                    }`}
                    data-testid={`repo-card-${repo.id}`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <h3 className={`font-mono text-sm font-bold ${isSelected ? 'text-[#F5A623]' : 'text-[#F2F1ED]'}`}>
                        {repo.full_name}
                      </h3>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {repo.private ? (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#FF5C5C]/10 text-[#FF5C5C] border border-[#FF5C5C]/30">
                            PRIVATE
                          </span>
                        ) : (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#37E2C4]/10 text-[#37E2C4] border border-[#37E2C4]/30">
                            PUBLIC
                          </span>
                        )}
                        {repo.language && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0B0D10] text-[#8E96A0] border border-[#232A35]">
                            {repo.language}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-[#8E96A0] line-clamp-2 leading-relaxed mb-3">
                      {repo.description}
                    </p>

                    <div className="flex items-center gap-4 text-xs font-mono text-[#8E96A0]">
                      <span className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 text-[#F5A623]" />
                        {repo.stars}
                      </span>
                      <span className="flex items-center gap-1">
                        <GitFork className="w-3.5 h-3.5" />
                        {repo.forks}
                      </span>
                      <span className="flex items-center gap-1">
                        <GitBranch className="w-3.5 h-3.5" />
                        {repo.default_branch}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Open PRs and Branches for Selected Repo (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          
          {/* Tabs and Create PR Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#232A35] pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('prs')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                  activeTab === 'prs'
                    ? 'bg-[#F5A623] text-[#0B0D10] shadow-[0_0_15px_rgba(245,166,35,0.3)]'
                    : 'bg-[#14171D] text-[#8E96A0] hover:text-[#F2F1ED] border border-[#232A35]'
                }`}
              >
                <GitPullRequest className="w-3.5 h-3.5" />
                <span>PULL REQUESTS ({pullRequests.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('branches')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                  activeTab === 'branches'
                    ? 'bg-[#37E2C4] text-[#0B0D10] shadow-[0_0_15px_rgba(55,226,196,0.3)]'
                    : 'bg-[#14171D] text-[#8E96A0] hover:text-[#F2F1ED] border border-[#232A35]'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>BRANCHES ({branches.length})</span>
              </button>
            </div>

            <button
              onClick={() => {
                setShowCreatePRModal(true);
                setCreatePRError(null);
              }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#14171D] hover:bg-[#1C222B] text-[#37E2C4] border border-[#37E2C4]/40 text-xs font-mono font-bold transition-all cursor-pointer hover:shadow-[0_0_15px_rgba(55,226,196,0.2)]"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>OPEN PULL REQUEST</span>
            </button>
          </div>

          {/* TAB 1: PULL REQUESTS */}
          {activeTab === 'prs' && (
            <div className="space-y-4" data-testid="pr-list">
              {isLoadingPRs ? (
                <div className="p-12 text-center text-xs font-mono text-[#8E96A0] animate-pulse border border-[#232A35] rounded-lg">
                  Fetching open PRs and diffs...
                </div>
              ) : pullRequests.length === 0 ? (
                <div className="p-12 text-center text-xs font-mono text-[#8E96A0] border border-[#232A35] rounded-lg bg-[#14171D] space-y-3">
                  <p>No open pull requests for this repository.</p>
                  <button
                    onClick={() => setActiveTab('branches')}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#0B0D10] text-[#37E2C4] border border-[#37E2C4]/40 hover:bg-[#37E2C4]/10 transition-colors"
                  >
                    <GitBranch className="w-3.5 h-3.5" />
                    <span>View and verify branches directly</span>
                  </button>
                </div>
              ) : (
                pullRequests.map((pr) => {
                  const isViolation = pr.scenario_type === 'violation';
                  const isStarting = isStartingJob === pr.number;

                  return (
                    <div
                      key={pr.number}
                      className="p-5 rounded-lg border border-[#2A3038] bg-[#14171D] hover:border-[#37E2C4]/40 transition-all space-y-4"
                      data-testid={`pr-card-${pr.number}`}
                    >
                      {/* Top PR Header */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3">
                          <img
                            src={pr.author_avatar}
                            alt={pr.author}
                            className="w-8 h-8 rounded-full border border-[#2A3038] mt-0.5 object-cover"
                          />
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-mono text-xs font-bold text-[#F5A623]">
                                #{pr.number}
                              </span>
                              <span className="text-xs font-mono text-[#8E96A0]">
                                by <strong className="text-[#F2F1ED]">@{pr.author}</strong>
                              </span>
                              <span className="text-xs font-mono text-[#8E96A0]">
                                • {pr.updated_at}
                              </span>
                            </div>
                            <h3 className="font-sans font-bold text-base text-[#F2F1ED] mt-1 leading-snug">
                              {pr.title}
                            </h3>
                          </div>
                        </div>

                        {/* Scenario Tag */}
                        <span className={`shrink-0 px-2 py-1 rounded text-[10px] font-mono font-bold tracking-wider uppercase border ${
                          isViolation 
                            ? 'bg-[#FF5C5C]/15 text-[#FF5C5C] border-[#FF5C5C]/40' 
                            : 'bg-[#37E2C4]/15 text-[#37E2C4] border-[#37E2C4]/40'
                        }`}>
                          {isViolation ? 'DEMO: VIOLATION' : 'VERIFIED TARGET'}
                        </span>
                      </div>

                      {/* Diff stats & branches */}
                      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#232A35] text-xs font-mono">
                        <div className="flex items-center gap-4 text-[#8E96A0]">
                          <span className="flex items-center gap-1.5">
                            <GitBranch className="w-3.5 h-3.5 text-[#8E96A0]" />
                            <code className="text-[#F2F1ED]">{pr.branch}</code>
                          </span>
                          <span className="flex items-center gap-1 text-[#37E2C4]">
                            <Plus className="w-3 h-3" />
                            {pr.additions}
                          </span>
                          <span className="flex items-center gap-1 text-[#FF5C5C]">
                            <Minus className="w-3 h-3" />
                            {pr.deletions}
                          </span>
                          <span>{pr.commits_count} commits</span>
                        </div>

                        {/* Verify Action Button */}
                        <button
                          onClick={() => handleTriggerVerification(pr.number)}
                          disabled={isStarting}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono font-bold text-xs shadow-[0_0_15px_rgba(55,226,196,0.3)] transition-all disabled:opacity-50 cursor-pointer"
                          data-testid={`verify-btn-${pr.number}`}
                        >
                          {isStarting ? (
                            <>
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              <span>ALLOCATING SANDBOX...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>VERIFY CODE</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* TAB 2: BRANCHES */}
          {activeTab === 'branches' && (
            <div className="space-y-3">
              {isLoadingBranches ? (
                <div className="p-12 text-center text-xs font-mono text-[#8E96A0] animate-pulse border border-[#232A35] rounded-lg">
                  Fetching repository branches from GitHub...
                </div>
              ) : branches.length === 0 ? (
                <div className="p-12 text-center text-xs font-mono text-[#8E96A0] border border-[#232A35] rounded-lg bg-[#14171D]">
                  No branches found.
                </div>
              ) : (
                branches.map((branch) => {
                  const isStarting = isStartingJob === branch.name;

                  return (
                    <div
                      key={branch.name}
                      className="p-4 rounded-lg border border-[#2A3038] bg-[#14171D] hover:border-[#37E2C4]/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-md bg-[#0B0D10] border border-[#232A35] text-[#37E2C4]">
                          <GitBranch className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-bold text-[#F2F1ED]">
                              {branch.name}
                            </span>
                            {branch.protected && (
                              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#F5A623]/10 text-[#F5A623] border border-[#F5A623]/30">
                                DEFAULT / PROTECTED
                              </span>
                            )}
                          </div>
                          {branch.commit_sha && (
                            <span className="text-[11px] font-mono text-[#8E96A0]">
                              HEAD: <code>{branch.commit_sha.substring(0, 7)}</code>
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {branch.name !== 'main' && (
                          <button
                            onClick={() => {
                              setNewPRHead(branch.name);
                              setNewPRTitle(`feat: merge ${branch.name} into main`);
                              setShowCreatePRModal(true);
                              setCreatePRError(null);
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#0B0D10] hover:bg-[#1C222B] text-xs font-mono text-[#8E96A0] hover:text-[#37E2C4] border border-[#232A35] transition-colors cursor-pointer"
                          >
                            <Plus className="w-3 h-3" />
                            <span>CREATE PR</span>
                          </button>
                        )}

                        <button
                          onClick={() => handleTriggerVerification(1)}
                          disabled={isStarting}
                          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono font-bold text-xs shadow-[0_0_15px_rgba(55,226,196,0.3)] transition-all cursor-pointer"
                        >
                          {isStarting ? (
                            <>
                              <RefreshCw className="w-3 h-3 animate-spin" />
                              <span>SANDBOX...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3 h-3" />
                              <span>VERIFY BRANCH</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

        </div>
      </div>

      {/* CREATE PULL REQUEST MODAL */}
      {showCreatePRModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#14171D] border-2 border-[#37E2C4]/50 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
            
            <div className="flex items-center justify-between border-b border-[#232A35] pb-4">
              <div className="flex items-center gap-2 text-sm font-mono text-[#37E2C4] font-bold">
                <GitPullRequest className="w-4 h-4" />
                <span>OPEN PULL REQUEST ON GITHUB</span>
              </div>
              <button
                onClick={() => setShowCreatePRModal(false)}
                className="text-[#8E96A0] hover:text-[#F2F1ED] text-xs font-mono px-2 py-1 rounded bg-[#0B0D10] border border-[#232A35]"
              >
                ✕ ESC
              </button>
            </div>

            <form onSubmit={handleCreatePRSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#8E96A0] uppercase mb-1">
                  Target Repository
                </label>
                <div className="px-3 py-2 rounded-lg bg-[#0B0D10] border border-[#232A35] text-xs font-mono text-[#F2F1ED]">
                  {selectedRepo?.full_name}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-[#8E96A0] uppercase mb-1">
                    Source Branch (Head)
                  </label>
                  <select
                    value={newPRHead}
                    onChange={(e) => setNewPRHead(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#0B0D10] border border-[#2A3038] text-xs font-mono text-[#F2F1ED] focus:border-[#37E2C4] outline-none"
                    required
                  >
                    {branches.map(b => (
                      <option key={b.name} value={b.name}>{b.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#8E96A0] uppercase mb-1">
                    Base Branch (Target)
                  </label>
                  <select
                    value={newPRBase}
                    onChange={(e) => setNewPRBase(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#0B0D10] border border-[#2A3038] text-xs font-mono text-[#37E2C4] font-bold focus:border-[#37E2C4] outline-none"
                    required
                  >
                    {branches.map(b => (
                      <option key={b.name} value={b.name}>{b.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#8E96A0] uppercase mb-1">
                  Pull Request Title *
                </label>
                <input
                  type="text"
                  placeholder="e.g. feat: implement AI verification logic and invariants"
                  value={newPRTitle}
                  onChange={(e) => setNewPRTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0B0D10] border border-[#2A3038] text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0]/50 focus:border-[#37E2C4] outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#8E96A0] uppercase mb-1">
                  Description / Invariant Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe the invariant guarantees or requirements implemented in this branch..."
                  value={newPRBody}
                  onChange={(e) => setNewPRBody(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0B0D10] border border-[#2A3038] text-xs font-mono text-[#F2F1ED] placeholder-[#8E96A0]/50 focus:border-[#37E2C4] outline-none resize-none"
                />
              </div>

              {createPRError && (
                <div className="p-3 rounded-lg bg-[#FF5C5C]/10 border border-[#FF5C5C]/40 text-[#FF5C5C] text-xs font-mono">
                  {createPRError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#232A35]">
                <button
                  type="button"
                  onClick={() => setShowCreatePRModal(false)}
                  className="px-4 py-2 rounded-lg bg-[#0B0D10] text-[#8E96A0] hover:text-[#F2F1ED] text-xs font-mono"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingPR || !newPRTitle.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-[#37E2C4] hover:bg-[#37E2C4]/90 text-[#0B0D10] font-mono font-bold text-xs shadow-[0_0_20px_rgba(55,226,196,0.4)] transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isCreatingPR ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>CREATING ON GITHUB...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-3.5 h-3.5" />
                      <span>CREATE PULL REQUEST</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
