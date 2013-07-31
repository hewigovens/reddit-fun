<html>
<body>
<center>
    <p>Full reddit topic rss feed:</p>
    <p>http://reddit.herokuapp.com/reddit/[topic_name]/[score_limit]</p>
    <form name='input' action='/add/' method='get'>
    <table>
        <tr>
            <td align="right"><p id="text">Topic:</p></td>
            <td align="left">
		        <input type="text" name="topic">
	        </td>
            </tr>
            <tr>
              <td align="right"><p id="text">Score Limit:</p></td>
              <td align="left"><input type="text" name="minimum_score"></td>
            </tr>
            <tr>
              <td align="right"><input type="submit" value="Get it"></td>
              <td align="left"><input type="reset" value="Reset"></></td>
            </tr>
    </table>
    </form>
</center>
</body>
</html>