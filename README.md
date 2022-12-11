        # Code-Challenge---Data-Engineer---Machinemax
 
 Code Challenge - Data Engineer -

Machinemax

Challenge - News Content Collect and Store:
Create a solution that crawls for articles from a news website, cleanses the response, stores in a
mongo database then makes it available to search via an API.

Instructions

• Candidate should put their test results on a public code repository hosted on Github
• Once test is completed please share the Github repository URL or a zip file.
• You are building a backend application and no UI is required, input can be provided using a
configuration file or command line

Details

• Write an application to crawl an online news website, e.g. www.theguardian.com/
au or www.bbc.com using a crawler framework such as [Scrapy] (http://scrapy.org/). You
can use a crawl framework of your choice and build the application in Python.
• The application should cleanse the articles to obtain only information relevant to the news
story, e.g. article text, author, headline, article url, etc. Use a framework such as Readability
to cleanse the page of superfluous content such as advertising and html
• Store the data in a hosted mongo database, e.g. compose.io/mongo, for subsequent
search and retrieval. Ensure the URL of the article is included to enable comparison to the
original.
• Write an API that provides access to the content preferably in a database. The user should
be able to search for articles by keyword

Evaluation:

• Coding standard, comments and style
• Unit testing strategy
• Overall solution design
• Code is easily understood and communicative (eg. comments, variable names, etc).
• Git commit history is consistent, easy to follow and understand.
