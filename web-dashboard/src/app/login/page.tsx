export default function LoginPage() {
  return <main style={{minHeight:"100svh",display:"grid",placeItems:"center",background:"#101210",color:"#f1f3ec",padding:24}}>
    <section style={{width:"100%",maxWidth:440,padding:36,border:"1px solid #353b33",borderRadius:20,background:"#191d18"}}>
      <p style={{color:"#b4db86",letterSpacing:".2em",fontSize:12}}>PODCAST NOTES</p>
      <h1 style={{fontSize:30,margin:"20px 0 8px"}}>登录你的播客工作台</h1>
      <p style={{color:"#b9c1b5",fontSize:14}}>整理声音，留下观点。使用工作台账号继续。</p>
      <form action="/auth/login" method="post">
        <label htmlFor="username" style={{display:"block",marginTop:24}}>用户名</label>
        <input id="username" name="username" autoComplete="username" required maxLength={100} style={{width:"100%",padding:13,marginTop:8,border:"1px solid #596351",borderRadius:9,background:"#101410",color:"inherit"}}/>
        <label htmlFor="password" style={{display:"block",marginTop:24}}>密码</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required maxLength={256} style={{width:"100%",padding:13,marginTop:8,border:"1px solid #596351",borderRadius:9,background:"#101410",color:"inherit"}}/>
        <button type="submit" style={{width:"100%",padding:14,marginTop:28,borderRadius:9,background:"#b4db86",color:"#14200f",fontWeight:700,cursor:"pointer"}}>登录工作台 →</button>
      </form>
      <p style={{marginTop:26}}><a href="/" style={{color:"#b4db86"}}>返回介绍页</a></p>
      <p style={{marginTop:16,color:"#b9c1b5",fontSize:14}}>私人工作台 · 暂不开放注册</p>
    </section>
  </main>;
}