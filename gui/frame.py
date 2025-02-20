
import sys,os,math,time
import json,re
import contextlib
import webbrowser
import time,threading

# from subprocess import Popen, PIPE, STDOUT, check_output
from subprocess import Popen, PIPE, STDOUT, check_output, DEVNULL
from glob import glob
from shutil import copytree

import tkinter as tk
from tkinter import Tk, END, StringVar, LEFT, TOP, BOTTOM, X, BOTH, YES, INSERT, W, E
from tkinter import Toplevel, Text, Entry, OptionMenu, Button

from tkinter import ttk
from tkinter.ttk import Label, LabelFrame, Scrollbar, Frame, Notebook, Style

from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
from tkinter.messagebox import showerror, showinfo, showwarning

from pathlib import Path
from os import getcwd, listdir, makedirs, symlink
from os.path import join, exists, dirname, abspath

from gui.utils import ftypes, filetypes, filetype, efiletype, batchsize, customRules
from gui.utils import USER_HOME, PIPELINER_HOME, PIPELINER_CONF, show
from gui.utils import dryrunFgColor, dryrunBgColor

################################
#Base Class for each Pipeline
################################

class PipelineFrame( Frame ) :
    def __init__( self, parent, pipeline_name, annotation, *args, **kwargs ) :
        self.global_info = kwargs.pop('global_info')
        Frame.__init__( self, parent, *args, **kwargs )
        self.parameters = []
        self.pipeline_name = pipeline_name
        
        #pipeline_name = kwargs['pipeline_name']
        pipepanel = self
        #pipeline_name = self.pfamily.get()
        #parent = (*args)[0]
        parent.add( pipepanel, text=pipeline_name )
        parent.pack( side=LEFT, fill=BOTH, padx=10, pady=10, expand=YES)
        
        datapath=StringVar()
        workpath=StringVar()
        targetspath=StringVar()
        
        self.datapath = datapath
        self.workpath = workpath
        self.targetspath = targetspath
        self.annotation = annotation   
        self.genome = annotation.get()
        
        l = Label( pipepanel, text="Data Directory:" )
        l.grid(row=1, column=1, sticky=W, padx=0, pady=10 )
        l = Label( pipepanel, text="Working Directory:" )
        l.grid(row=3, column=1, sticky=W, padx=0, pady=10 )
        
        self.dry_button = dry_button = Button(self, 
                                              text="Dry Run", 
                                              command=self.dryrun, 
                                              state='disabled' )
        dry_button.grid(row=4, column=4, sticky=E)
        
        self.run_button = run_button = Button(self, 
                                              text="Run", 
                                              command=self.runslurm, 
                                              state='disabled' )
        run_button.grid( row=4, column=5 )
        
        data_entry = Entry(pipepanel, 
                           bd =2, 
                           width = 50, 
                           #bg = entryBgColor, 
                           #fg = entryFgColor, 
                           textvariable = datapath, state='readonly'
                          )
        
        self.work_entry = work_entry = Entry(pipepanel, 
                           bd =2, 
                           width=50, 
                           #bg=entryBgColor, 
                           #fg=entryFgColor,
                           textvariable=workpath, state='readonly'
                          )
        
        data_entry.grid( row=1, column=2, columnspan=3 )
        self.data_button = data_button = Button( pipepanel, 
                             text="Open Directory", 
                             command=self.set_data_directory )
        data_button.grid( row=1, column=5 )
        
        data_count_label = Label( pipepanel, text="FastQ files Found:" )
        data_count_label.grid( row=2, column=1 )
        data_count = Label( pipepanel, text="0" )
        data_count.grid( row=2, column=2 )
        self.data_count = data_count
        
        work_entry.grid( row=3, column=2, columnspan=3 )
        self.work_button = work_button = Button( pipepanel, 
                             text="Initialize Directory",
                             command=self.init_work_dir
                            )
        work_button.grid( row=3, column=5 )
        work_button.config( state="disabled" ) #( "disabled" )
        

    def set_data_directory( self ):
        fname = askdirectory( initialdir = USER_HOME, 
                             title="Select Data Directory")
        self.datapath.set(fname)                                    
        #count number
        self.data_count['text'] = str(
            len([fn for fn in listdir(fname) if fn.endswith(filetype)] )
        ) 
        print( "Found", self.data_count['text'], filetype, "files!" )
        
        self.option_controller()
        
    def option_controller( self, *args, **kwargs ) :
        '''
        controls active buttons
        '''
        print( 'option controller:', self.data_count['text'], 'found!!!' )
        print( 'option controller:', self.workpath.get() )
        if self.data_count['text'] != '0' :
            self.work_button.config( state="active" )
            
        if self.workpath.get() :
            self.dry_button.config( state='active' )
            self.work_entry.config( state='normal' )
        
    def init_work_dir( self ):
        #Getting the work directory user input
        #and basic emptyness checking
        fname = self.workpath.get()
        if not fname :
            #self.work_entry.config( state='normal' )
            fname = askdirectory( initialdir=USER_HOME, 
                 title="Select Work Directory")    
            self.workpath.set(fname)
        
        error = 'Error'
        error_msg = ''
        if exists(fname) :
            if len(listdir(fname))==0 :
                pass
            else :
                error = "WARNING!"
                error_msg ="The work directory not initialized!" 
                showwarning( error, error_msg )
        else :
            try :
                makedirs( fname )
            except OSError :
                error_msg = 'Failed to make a new directory: "%s"' % fname
                error_msg += 'Check if you have a write permission in the directory.'
                showerror( error, error_msg )
        
        self.option_controller()
        #print( 'fname in init_work_dir exomeseq:', fname )
        if error_msg :
            return
        
        try :
            #need to be solved by making an empty dir in the Results-template
            makedirs( join(fname, "QC") ) 
            #os.mknod can replace but OSX needs a super user prev.
            #open( join(fname, "pairs"), 'w' ).close() 
            #open( join(fname, "samples"), 'w' ).close()
            
            print( "copying", 'template', "into", fname )
            os.system( "cp -r %s/Results-template/* %s"%(PIPELINER_HOME, fname ) )
                
        except :
            showerror( "Initialization failed!", "Work directory data structure generation has failed." )
            return
        
        if self.make_symlinks() :
            showinfo( "Success", "The work directory has successfully initialized!")
        else :
            showerror( "Symlink failed", "" )
    
    
        
    def makejson(self, *args):
        #print(args[0])
        caller=args[0]
        #global PD
        #global UnitsBak
        #global RGbak
        D=dict()
        try:
            F=open(self.workpath.get()+"/samples","r")
            f=F.read().split("\n")
            F.close()
            for line in f:
                L=line.split()
                a=L.pop(0)
                D[a]=L
                samples=D
        except:
            samples={"na":"na"}

        D=dict()
        try:
            F=open(self.workpath.get()+"/pairs","r")
            f=F.read().split()
            F.close()
            for i in range(0,len(f),2):
    #            a=f[i].split(".")[0]
    #            b=f[i+1].split(".")[0]
                a=f[i]
                b=f[i+1]

                D[a+"+"+b]=[a,b]

            pairs=D
        except:
            pairs={"na":"na"}   

        D=dict()
        try:
            F=open(self.workpath.get()+"/contrasts.tab","r")
    #        f=F.read().split('\n')
    #        F.close()
    #        D["rsamps"]=f[0].split()
    #        D["rgroups"]=f[1].split()
    #        D["rcontrasts"]=f[2].split()
    #        D["rlabels"]=f[3].split()        
            f=F.readlines()
            F.close()
    ##        sampl=[]
    ##        grp=[]
            cont=[]
    ##        lbl=[]
            for x in f:
                  if len(x.split()) == 2:
                     cont.append(x.split()[0])
                     cont.append(x.split()[1])
            D["rcontrasts"]=cont
    #        contrasts["rcontrasts"]=cont
            contrasts=D
        except:
            contrasts={"rcontrasts":"na"}
    ##        contrasts={"rsamps":"na","rgroups":"na","rcontrasts":"na","rlabels":"na"}   
    ##------
        D=dict()
        try:
            F=open(self.workpath.get()+"/groups.tab","r")
            f=F.readlines()
            F.close()
            sampl=[]
            grp=[]
    #        cont=[]
            lbl=[]
            for x in f:
    #           if len(x.split()) == 4 or len(x.split()) == 3:
                if len(x.split()) == 3:  
                    sampl.append(x.split()[0])
                    grp.append(x.split()[1])
                    lbl.append(x.split()[2])
            D["rsamps"]=sampl
            D["rgroups"]=grp
            D["rlabels"]=lbl
    #        D["rcontrasts"]="na"
    #        contrasts=D
            groups=D
        except:
    #        contrasts={"rsamps":"na","rgroups":"na","rcontrasts":"na","rlabels":"na"}
            groups={"rsamps":"na","rgroups":"na","rlabels":"na"}          
    ##------   
        D=dict() 
        FT = filetype#.get()
    #    p = Popen("ls "+workpath.get()+"/*."+FT, shell=True, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, close_fds=True)
        p = Popen("find "+self.workpath.get()+" -maxdepth 1 -type l -printf '%f\n' ", shell=True, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, close_fds=True)
        a = p.stdout.read().decode(encoding='UTF-8').split("\n")

        RG=dict()   
        b=a.pop()
    #    tkinter.messagebox.showerror("",a)
    #    if freezeunits.get()=="no":
        for i in a:

            key=re.sub(".realign","",i.split("/")[-1])
            key=re.sub(".bai","",key)
            key=re.sub(".bam","",key)
            key=re.sub(".sam","",key)        
            key=re.sub(".recal","",key)
            key=re.sub(".dedup","",key)
            key=re.sub(".sorted","",key)
            key=re.sub(".fin","",key)
            key=re.sub(".R[12]","",key)
            key=re.sub("_R[12]","",key)
            key=re.sub(".fastq","",key)
            key=re.sub(".gz","",key)                                
    #        key=re.sub("[\._](R[12]\.)*"+FT+"$","",i.split("/")[-1])        
    #        key=re.sub(".R[12]."+FT+"$","",i.split("/")[-1])
    #        key=re.sub("([._]R[12][._])*([fin|sorted|dedup|recal|realign])*\.{0}$".format(FT),"",i.split("/")[-1])
            D[key]=key
            RG[key]={'rgsm':key,'rglb':'na','rgpu':'na','rgpl':'ILLUMINA','rgcn':'na'}
        units=D
        UnitsBak=D

        try:
            F=open(self.workpath.get()+"/rg.tab","r")
            f=F.read().splitlines()
            F.close()
            for theLine in f:
                if not re.match("^ID",theLine):
                    (rgid,rgsm,rglb,rgpl,rgpu,rgcn)=theLine.split("\t")
                    RG[rgid]={'rgsm':rgsm,'rglb':rglb,'rgpu':rgpu,'rgpl':rgpl,'rgcn':rgcn}
        except:
            pass
        
        RGbak=RG
    #     else:
    #         units=UnitsBak
    #         RG=RGbak
    # 
        PD=dict()

        smparams=[]

        for i in range(len(self.parameters)):

            if cp[i].var.get()=="1":
                smparams.append(parameters[i])
                
        AD=eval( open( join(PIPELINER_HOME, 
                            self.annotation.get()+".json"
                           ), "r"
                     ).read()
               )
        
        SD=AD['references']['rnaseq']['STARDIR']
    #    tkinter.messagebox.showinfo("initLock","SD={0}".format(SD))
        gi = self.global_info 
        PD={'project': 
            {'pfamily': gi.pfamily.get(),
             'units': units, 
             'samples': samples, 
             'pairs': pairs, 
             'id': gi.eprojectid.get(), 
             'pi': gi.epi.get(), 
             'organism': gi.eorganism.get(), 
             'analyst': gi.eanalyst.get(), 
             'poc': gi.epoc.get(), 
             'pipeline': self.Pipeline.get(), 
             'version':"1.0", 
             'annotation': gi.annotation.get(), 
             'datapath': self.datapath.get(), 
             'targetspath': self.targetspath.get(), 
             'filetype': filetype , 
             'binset': "standard-bin", 
             'username': gi.euser.get(), 
             'flowcellid': gi.eflowcell.get(), 
             'platform': gi.eplatform.get(), 
             'custom': customRules, 
             'efiletype': efiletype, 
             'workpath': self.workpath.get(), 
             'batchsize': batchsize, 
             "smparams": smparams, 
             "rgid": RG, 
             "cluster": "cluster_medium.json", 
             "description": gi.description.get('1.0',END), 
             "technique" : gi.technique.get(), 
             "TRIM": "yes", 
            }
           } 
        J=json.dumps(PD, sort_keys = True, indent = 4, ensure_ascii=True)
        gi.jsonconf.delete("1.0", END)    
        gi.jsonconf.insert(INSERT, J)
        self.saveproject(gi.jsonconf.get("1.0",END))
    
    def make_symlinks(self):
        pl = self.pipeline_name
        data = self.datapath.get()
        
        if pl != 'ChIPSeq' :
            data=data+"/"
            data=re.sub("/+$","/",data)
            FT=filetype
            try:
                #cmd="for f in `ls "+data+"*.fastq`;do ln -s $f;done"
        #        cmd="for f in `ls "+data+"*."+FT+"`;do ln -s $f ../;done"
                labelfile=Path(self.datapath.get()+"/labels.txt")
                if labelfile.is_file():
                    cmd="perl {3}/symfiles.pl {0} {1} {2}".format( 
                        self.datapath.get(), self.datapath.get() + "/labels.txt", self.workpath.get(), PIPELINER_HOME )
                    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                    Out = p.stdout.read()
                else:
                    cmd="for f in `ls {0}*[._]{1}`;do ln -s $f {2};done".format(data,FT, self.workpath.get())        
                    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                    Out = p.stdout.read()

            except Exception as e: 
                showerror("Error",str(e))
                if str(Out).find("No such file")==-1:
                    showinfo(FT,"Symlinks Created")
                else:
                    showerror("Error","Symlinks Not Created")
                if re.sub("bam","",FT):
                    FT2=re.sub("bam","",FT)
                    try:
                        cmd="for f in `ls "+data+"*."+FT2+"bai`;do ln -s $f %s;done"%self.workpath.get()
                        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                        Out = p.stdout.read()
                    except Exception as e:
                        showerror("Error",str(e))
                    if str(Out).find("No such file")==-1:    
                        showinfo(FT2+"bai","Symlinks Created")
                #else:
                    #tkinter.messagebox.showinfo(FT2+"bai","Index Symlinks Not Created")
            p = os.popen("for f in `ls {0}/*fastq*`;do mv $f `echo $f | sed s/_fastq/.fastq/g` ; done ".format( self.workpath.get() ))
            p = os.popen("for f in `ls {0}/*fastq*`;do mv $f `echo $f|sed s/_R1.fastq/.R1.fastq/g`; done ".format( self.workpath.get() ))
            p = os.popen("for f in `ls {0}/*fastq*`;do mv $f `echo $f|sed s/_R2.fastq/.R2.fastq/g`; done ".format( self.workpath.get() ))
        else :
            from glob import glob
            from os.path import basename
            from os import symlink
            fastq_files = glob(data+'/*.fastq*')
            files = []

            for fastq in fastq_files :
                try :
                    src = fastq
                    trg = self.workpath.get() +"/"+ basename(fastq)
                    symlink( src, trg )
                    files.append( trg )
                except :
                    showerror( "ChIPSeq", "Error in Making symlink %s -> %s!"%(src,trg) )
                    return

            symlink(PIPELINER_HOME + '/../ChIP-Seq-Pipeline/main.nf', self.workpath.get() + '/main.nf')
            showinfo( "ChIPSeq", "ChIP-seq input files:\n%s" % "\n".join(files) )

        #self.makejson("none")
        return True
        
    def writepaste( self, ftype, comments ) :
        try:
            fname=self.workpath.get()+"/"+ftype    
            F=open(fname,"w")
            F.write(comments.get('1.0',END))
            F.close()
            showinfo("Success","Wrote file "+fname)
        except:
            showerror("Error","Did not write file "+fname+"\nIs working directory set?")
            
        #self.makejson("none")
        return

    def readpaste( self, ftype, comments ):
        try:
            fname = self.workpath.get()+"/"+ftype
            F=open(fname,"r")
            comments.delete("1.0", END)    
            comments.insert(INSERT, F.read())
            F.close()
            showinfo("Success","Read file "+fname)
        except:
            showerror("Error","Did not read file "+fname+"\nIs working directory set?")
            
        #self.makejson("none")
        return
    
    def dryrun( self ) :
        self.makejson("none")
        self.run_button.config( state='active' )
        return self.cmd( "--dryrun -s %s/Snakefile --rerun-incomplete -d %s" % ( self.workpath.get(), self.workpath.get())) 
    
    def runslurm( self ) :
        #global snakemakeRun
        #global runmode
        runmode=2
        pl=self.Pipeline.get()
        PL=USER_HOME
        
        if self.checklist()==1:
            return

        if pl == 'ChIPSeq' :
            showinfo('ChIPSeq', "Starting Nextflow Run "+pl+"\n")
            cmd = "nextflow run ../ChIP-Seq-Pipeline/main.nf --reads='%s/*.fastq*' --macsconfig='%s/peakcallinfo.csv' -config ../ChIP-Seq-Pipeline/config --genome='hg19' &" %(  self.workpath.get(), self.workpath.get() )
            print( cmd )
            showinfo('ChIPSeq', "Starting Nextflow Run:\n"+"%s\n"+cmd)
            os.system(cmd)
        else :
            MkaS=os.popen(PIPELINER_HOME+"/makeasnake.py "+PL+" 2>&1 | tee -a "+self.workpath.get()+"/Reports/makeasnake.log").read()
            showinfo("Slurm","Starting Slurm Snakemake Run "+pl+"\n")
            #snakemakeRun=Popen("../qsub.sh")
            snakemakeRun=Popen(self.workpath.get()+"/submit_slurm.sh")    
            #seelog()    
            
    def cmd(self, smcommand):
        pl=self.pipeline_name

        print(pl)
        PL=USER_HOME #uhome
    #    makejson("none")
        if self.checklist()==1:
            return
        self.saveproject(self.global_info.jsonconf.get("1.0",END))
        #MkaS=os.popen("./makeasnake.py 2>&1 | tee -a "+workpath.get()+"/Reports/makeasnake.log").read()
        if pl == 'ChIPSeq' :
            showinfo('ChIPSeq', "Testing "+pl+"\n")
        else :
            MkaS=os.popen(PIPELINER_HOME+"/makeasnake.py "+PL+" 2>&1 | tee -a "+self.workpath.get()+"/Reports/makeasnake.log").read()
            Out=os.popen("cd "+self.workpath.get()+" && snakemake " + smcommand +" 2>&1").read()
            show(Out,"CCBR Pipeliner: "+ pl + " "+smcommand,dryrunFgColor,dryrunBgColor,200,100)
            
    def checklist( self ) :
        '''placeholder'''
        return 0

    def saveproject( self, proj ):
        print( proj )
        P=eval(proj)
        try:
            # with open('project.json', 'w') as F:
            with open(USER_HOME+'/project.json', 'w') as F:
                json.dump(P, F, sort_keys = True, indent = 4, ensure_ascii=False)
            F.close()
            #showinfo("Project Json Write","Project Json file written.")
        except:
            showerror("Error","Project Json file not written.")
